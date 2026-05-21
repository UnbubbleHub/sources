"""Claude E2E pipeline implementation."""

import logging
import os
import time
from typing import cast

import anthropic
from anthropic.types import WebSearchToolResultBlock

from unbubble_sources.annotator.claude import ClaudeAnnotator
from unbubble_sources.data import (
    AnnotatedSource,
    APICallUsage,
    Article,
    DiversityReport,
    NewsEvent,
    RunResult,
    SearchQuery,
    Source,
    Usage,
)
from unbubble_sources.metrics.base import Metric, MetricResult
from unbubble_sources.metrics.runner import MetricsRunner
from unbubble_sources.pipeline._report import build_diversity_report
from unbubble_sources.pricing import PriceCache
from unbubble_sources.ranker.mmr import MMRRanker
from unbubble_sources.run_logger import RunLogger
from unbubble_sources.stream_logger import StreamLogger
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
        fallback_annotator: Optional annotator used only when
            ``annotator`` is absent. The ranker is **skipped** on
            fallback-annotated sources; the fallback exists so metrics
            that need annotations (e.g. the political compass) still
            have usable input when the diversity step is disabled.
        ranker: Optional MMR diversity ranker.
        ranker_top_k: Number of sources to return from ranker.
        metrics: Metrics to compute over the final source set.
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
        fallback_annotator: ClaudeAnnotator | None = None,
        ranker: MMRRanker | None = None,
        ranker_top_k: int = 10,
        metrics: list[Metric] | None = None,
        run_logger: RunLogger | StreamLogger | None = None,
        price_cache: PriceCache | None = None,
    ) -> None:
        resolved_key = api_key or os.environ.get("CLAUDE_API_KEY")
        self._client = anthropic.AsyncAnthropic(api_key=resolved_key)
        self._model = model
        self._target = target_articles
        self._annotator = annotator
        self._fallback_annotator = fallback_annotator
        self._ranker = ranker
        self._ranker_top_k = ranker_top_k
        self._metrics: list[Metric] = metrics or []
        self._run_logger = run_logger
        self._price_cache = price_cache

    async def run(
        self,
        event: NewsEvent,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> RunResult:
        """Execute the E2E pipeline.

        Args:
            event: The news event to investigate.
            from_date: Optional start date filter.
            to_date: Optional end date filter.

        Returns:
            A ``RunResult`` wrapping the final sources, accumulated
            usage, computed metrics, and the diversity report.
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

        # Annotate sources (main → fallback → none); ranker only runs on
        # main-annotator output. See the composable pipeline for the
        # exact same control flow.
        annotated_sources: list[AnnotatedSource] | None = None
        annotator_name: str | None = None
        fallback_used = False

        active_annotator = self._annotator or self._fallback_annotator
        if active_annotator is not None and final_articles:
            fallback_used = self._annotator is None and self._fallback_annotator is not None
            annotator_name = type(active_annotator).__name__
            stage_label = "annotation_fallback" if fallback_used else "annotation"

            t0 = time.monotonic()
            annotated_sources, annotation_usage = await active_annotator.annotate(
                final_articles, event.description
            )
            annotation_duration = time.monotonic() - t0

            if self._price_cache:
                self._price_cache.stamp_usage(annotation_usage)
            total_usage += annotation_usage

            if self._run_logger:
                self._run_logger.log_stage(
                    stage=stage_label,
                    component=annotator_name,
                    input_data={"source_count": len(final_articles)},
                    output_data=annotated_sources,
                    usage=annotation_usage,
                    duration_seconds=annotation_duration,
                )

        # Rank by diversity — only when the main annotator ran.
        ranked_sources: list[AnnotatedSource] | None = None
        if (
            annotated_sources is not None
            and self._ranker is not None
            and not fallback_used
        ):
            t0 = time.monotonic()
            ranked_sources = self._ranker.rank(annotated_sources, self._ranker_top_k)
            rank_duration = time.monotonic() - t0

            if self._run_logger:
                self._run_logger.log_stage(
                    stage="ranking",
                    component="MMRRanker",
                    input_data={"source_count": len(annotated_sources)},
                    output_data=ranked_sources,
                    usage=None,
                    duration_seconds=rank_duration,
                )

        sources_for_metrics: list[AnnotatedSource]
        final_sources: list[Source]
        if ranked_sources is not None:
            sources_for_metrics = ranked_sources
            final_sources = cast(list[Source], ranked_sources)
        elif annotated_sources is not None:
            sources_for_metrics = annotated_sources
            final_sources = cast(list[Source], annotated_sources)
        else:
            sources_for_metrics = []
            final_sources = final_articles

        metric_results: list[MetricResult] = []
        if self._metrics and sources_for_metrics:
            runner = MetricsRunner(self._metrics, run_logger=self._run_logger)
            metric_results = runner.run(sources_for_metrics)

        diversity_report: DiversityReport = build_diversity_report(
            annotator_name=annotator_name,
            fallback_used=fallback_used,
            ranker=self._ranker if not fallback_used else None,
            ranker_top_k=self._ranker_top_k,
            annotated_sources=sources_for_metrics,
            total_source_count=len(final_sources),
        )
        if self._run_logger:
            self._run_logger.log_diversity_report(diversity_report)
            self._run_logger.finish_run(final_sources, total_usage)

        return RunResult(
            sources=final_sources,
            usage=total_usage,
            metrics=metric_results,
            diversity_report=diversity_report,
        )
