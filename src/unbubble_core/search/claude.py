from __future__ import annotations

import logging
import os

import anthropic
from anthropic.types import WebSearchResultBlock

from unbubble_core.data import Article, SearchQuery
from unbubble_core.url import extract_domain

logger = logging.getLogger(__name__)

class ClaudeSearcher:
    """Search for news articles using Claude's built-in web search tool.

    This uses Anthropic's server-side web search, so you only need your
    existing Claude API key - no separate news API required.

    Note: Web search must be enabled in your Anthropic Console settings.
    Cost: $10 per 1,000 searches (plus standard token costs).

    Args:
        api_key: Anthropic API key (defaults to CLAUDE_API_KEY env var).
        model: Model to use for search (default: claude-haiku-4-5-20251001).
        max_searches_per_query: Max web searches per query (default: 1).
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        model: str = "claude-haiku-4-5-20251001",
        max_searches_per_query: int = 1,
    ) -> None:
        resolved_key = api_key or os.environ.get("CLAUDE_API_KEY")
        self._client = anthropic.AsyncAnthropic(api_key=resolved_key)
        self._model = model
        self._max_searches = max_searches_per_query

    async def search(
        self,
        queries: list[SearchQuery],
        *,
        from_date: str | None = None,
        to_date: str | None = None,
        max_results_per_query: int = 10,
    ) -> list[Article]:
        """Search for articles matching the given queries.

        Args:
            queries: List of search queries to execute.
            from_date: Start date filter (included in search prompt).
            to_date: End date filter (included in search prompt).
            max_results_per_query: Maximum articles to return per query.

        Returns:
            Deduplicated list of articles found across all queries.
        """
        seen_urls: set[str] = set()
        articles: list[Article] = []

        for query in queries:
            try:
                query_articles = await self._search_single(
                    query,
                    from_date=from_date,
                    to_date=to_date,
                    max_results=max_results_per_query,
                )
                for article in query_articles:
                    if article.url not in seen_urls:
                        seen_urls.add(article.url)
                        articles.append(article)
            except Exception as e:
                # Skip failed queries
                logger.warning(f"Failed query {query}. Error: {e}")
                continue

        return articles

    async def _search_single(
        self,
        query: SearchQuery,
        *,
        from_date: str | None,
        to_date: str | None,
        max_results: int,
    ) -> list[Article]:
        """Execute a single search query using Claude's web search."""
        # Build the search prompt
        date_context = ""
        if from_date and to_date:
            date_context = f" from {from_date} to {to_date}"
        elif from_date:
            date_context = f" from {from_date} onwards"
        elif to_date:
            date_context = f" until {to_date}"

        user_prompt = (
            f"Search for news articles about: {query.text}{date_context}\n\n"
            f"Find up to {max_results} relevant news articles. "
            "For each article found, provide the title, URL, source name, "
            "publication date, and a brief description. "
            "Format your response as a structured list."
        )

        response = await self._client.messages.create(
            model=self._model,
            max_tokens=2048,
            tools=[
                {
                    "type": "web_search_20250305",
                    "name": "web_search",
                    "max_uses": self._max_searches,
                }
            ],
            messages=[{"role": "user", "content": user_prompt}],
        )

        # Extract articles from web search results
        articles: list[Article] = []

        for block in response.content:
            if block.type == "web_search_tool_result":
                content = block.content
                if isinstance(content, list):
                    for result in content:
                        article = self._parse_search_result(result, query)
                        articles.append(article)

        return articles[:max_results]

    def _parse_search_result(self, result: WebSearchResultBlock, query: SearchQuery) -> Article:
        """Parse a web search result into an Article."""

        return Article(
            title=result.title,
            url=result.url,
            source=extract_domain(result.url),
            published_at=result.page_age,
            description=None,  # encrypted_content is not human-readable
            query=query,
        )
