"""Claude E2E pipeline implementation."""

import logging
import os
import time
from typing import cast

import anthropic
from anthropic.types import WebSearchToolResultBlock

from unbubble_sources.annotator.claude import ClaudeAnnotator
from unbubble_sources.data import APICallUsage, Article, NewsEvent, SearchQuery, Source, Usage
from unbubble_sources.pricing import PriceCache
from unbubble_sources.ranker.mmr import MMRRanker
from unbubble_sources.run_logger import RunLogger
from unbubble_sources.url import extract_domain

logger = logging.getLogger(__name__)


class ClaudeE2EPipeline:
    """Single Claude call that generates queries and searches in one pass.

    This pipeline uses Claude's web search tool directly, instructing it to
    find diverse articles about a news event in a single API call.
    Optionally annotates and ranks results by perspective diversity.

    Args:
        model: Anthropic model to use.
        api_key: API key (defaults to CLAUDE_API_KEY env var).
        target_articles: Target number of diverse articles to find.
        annotator: Optional Claude-based source annotator.
        ranker: Optional MMR diversity ranker.
        ranker_top_k: Number of sources to return from ranker.
        run_logger: Optional RunLogger for intermediate result logging.
        price_cache: Optional PriceCache for cost estimation.
    """

    SYSTEM_PROMPT = """\
You are a research assistant finding diverse news coverage of events.
Given a news event, search for and return {target_articles} diverse articles
that cover the SAME factual event from DIFFERENT perspectives.

Ensure diversity across:
- Political/ideological viewpoints
- Geographic perspectives
- Source types (mainstream, independent, international)
- Framing (economic, social, political, humanitarian)

Use web search to find real, current articles. Return articles that cover
the same underlying facts but from genuinely different angles.\
"""

    def __init__(
        self,
        model: str = "claude-haiku-4-5-20251001",
        api_key: str | None = None,
        target_articles: int = 10,
        *,
        annotator: ClaudeAnnotator | None = None,
        ranker: MMRRanker | None = None,
        ranker_top_k: int = 10,
        run_logger: RunLogger | None = None,
        price_cache: PriceCache | None = None,
    ) -> None:
        resolved_key = api_key or os.environ.get("CLAUDE_API_KEY")
        self._client = anthropic.AsyncAnthropic(api_key=resolved_key)
        self._model = model
        self._target = target_articles
        self._annotator = annotator
        self._ranker = ranker
        self._ranker_top_k = ranker_top_k
        self._run_logger = run_logger
        self._price_cache = price_cache

    async def run(
        self,
        event: NewsEvent,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> tuple[list[Source], Usage]:
        """Execute the E2E pipeline.

        Args:
            event: The news event to investigate.
            from_date: Optional start date filter.
            to_date: Optional end date filter.

        Returns:
            Tuple of (diverse sources, usage).
        """
        if self._run_logger:
            self._run_logger.start_run("claude_e2e", event)

        # Ensure prices are fetched before pipeline starts
        if self._price_cache:
            await self._price_cache.get()

        # Build user prompt
        date_context = ""
        if from_date and to_date:
            date_context = f"\nDate range: {from_date} to {to_date}"
        elif from_date:
            date_context = f"\nFrom date: {from_date}"
        elif to_date:
            date_context = f"\nUntil date: {to_date}"

        user_prompt = f"Find diverse news coverage of: {event.description}"
        if event.date:
            user_prompt += f"\nEvent date: {event.date}"
        if event.context:
            user_prompt += f"\nContext: {event.context}"
        user_prompt += date_context

        t0 = time.monotonic()
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=self.SYSTEM_PROMPT.format(target_articles=self._target),
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": min(self._target, 5),  # Limit searches
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Extract usage from response
        web_searches = 0
        server_tool_use = getattr(response.usage, "server_tool_use", None)
        if server_tool_use is not None:
            web_searches = getattr(server_tool_use, "web_search_requests", 0) or 0

        usage = Usage(
            api_calls=[
                APICallUsage(
                    model=self._model,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    cache_creation_input_tokens=getattr(
                        response.usage, "cache_creation_input_tokens", 0
                    )
                    or 0,
                    cache_read_input_tokens=getattr(response.usage, "cache_read_input_tokens", 0)
                    or 0,
                    web_searches=web_searches,
                ),
            ],
        )

        # Extract articles from search results
        articles: list[Source] = []
        seen_urls: set[str] = set()

        # Create a dummy query for attribution
        dummy_query = SearchQuery(text=event.description, intent="e2e search")

        for block in response.content:
            if isinstance(block, WebSearchToolResultBlock):
                content = block.content
                if isinstance(content, list):
                    for result in content:
                        seen_urls.add(result.url)
                        articles.append(
                            Article(
                                title=result.title or "",
                                url=result.url,
                                source=extract_domain(result.url),
                                published_at=result.page_age,
                                description=None,
                                query=dummy_query,
                            )
                        )

        final_articles = articles[: self._target]
        e2e_duration = time.monotonic() - t0

        if self._price_cache:
            self._price_cache.stamp_usage(usage)

        if self._run_logger:
            self._run_logger.log_stage(
                stage="e2e",
                component="ClaudeE2EPipeline",
                input_data=event,
                output_data=final_articles,
                usage=usage,
                duration_seconds=e2e_duration,
            )

        total_usage = usage

        # Annotate sources (optional)
        if self._annotator and final_articles:
            t0 = time.monotonic()
            annotated_sources, annotation_usage = await self._annotator.annotate(
                final_articles, event.description
            )
            annotation_duration = time.monotonic() - t0

            if self._price_cache:
                self._price_cache.stamp_usage(annotation_usage)
            total_usage += annotation_usage

            if self._run_logger:
                self._run_logger.log_stage(
                    stage="annotation",
                    component="ClaudeAnnotator",
                    input_data={"source_count": len(final_articles)},
                    output_data=annotated_sources,
                    usage=annotation_usage,
                    duration_seconds=annotation_duration,
                )

            # Rank by diversity (optional, requires annotation)
            if self._ranker:
                t0 = time.monotonic()
                ranked = self._ranker.rank(annotated_sources, self._ranker_top_k)
                rank_duration = time.monotonic() - t0

                if self._run_logger:
                    self._run_logger.log_stage(
                        stage="ranking",
                        component="MMRRanker",
                        input_data={"source_count": len(annotated_sources)},
                        output_data=ranked,
                        usage=None,
                        duration_seconds=rank_duration,
                    )

                final_sources: list[Source] = cast(list[Source], ranked)
            else:
                final_sources = cast(list[Source], annotated_sources)
        else:
            final_sources = final_articles

        if self._run_logger:
            self._run_logger.finish_run(final_sources, total_usage)

        return (final_sources, total_usage)
