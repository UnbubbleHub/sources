"""Claude E2E pipeline implementation."""

import logging
import os

import anthropic
from anthropic.types import WebSearchToolResultBlock

from unbubble_sources.data import Article, NewsEvent, SearchQuery
from unbubble_sources.url import extract_domain

logger = logging.getLogger(__name__)

class ClaudeE2EPipeline:
    """Single Claude call that generates queries and searches in one pass.

    This pipeline uses Claude's web search tool directly, instructing it to
    find diverse articles about a news event in a single API call.

    Args:
        model: Anthropic model to use.
        api_key: API key (defaults to CLAUDE_API_KEY env var).
        target_articles: Target number of diverse articles to find.
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
    ) -> None:
        resolved_key = api_key or os.environ.get("CLAUDE_API_KEY")
        self._client = anthropic.AsyncAnthropic(api_key=resolved_key)
        self._model = model
        self._target = target_articles

    async def run(
        self,
        event: NewsEvent,
        *,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> list[Article]:
        """Execute the E2E pipeline.

        Args:
            event: The news event to investigate.
            from_date: Optional start date filter.
            to_date: Optional end date filter.

        Returns:
            List of diverse articles.
        """
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

        # Extract articles from search results
        articles: list[Article] = []
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

        return articles[: self._target]
