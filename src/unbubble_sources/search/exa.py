"""Exa search using the official exa-py SDK."""

import asyncio
import logging
import os
from urllib.parse import urlparse

from exa_py import AsyncExa

from unbubble_sources.data import Article, SearchQuery, Source, Usage

logger = logging.getLogger(__name__)


class ExaSearcher:
    """Search for content using the Exa API.

    Uses the ``exa-py`` async SDK to query the Exa search engine, which
    returns web pages with title, URL, and published date.

    Args:
        api_key: Exa API key (defaults to EXA_API_KEY env var).
        max_results_per_query: Default max results per query (default 10).
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        max_results_per_query: int = 10,
    ) -> None:
        self._api_key = api_key or os.environ.get("EXA_API_KEY")
        if not self._api_key:
            raise ValueError("Exa API key required. Pass api_key or set EXA_API_KEY env var.")
        self._max_results = max_results_per_query
        self._client = AsyncExa(api_key=self._api_key)

    async def search(
        self,
        queries: list[SearchQuery],
        *,
        from_date: str | None = None,
        to_date: str | None = None,
        max_results_per_query: int = 10,
    ) -> tuple[list[Source], Usage]:
        """Search for content matching the given queries.

        Args:
            queries: List of search queries to execute.
            from_date: Start date filter (ISO format, e.g. "2026-01-01").
            to_date: End date filter (ISO format).
            max_results_per_query: Maximum results to return per query.

        Returns:
            Tuple of (deduplicated articles, usage).
        """
        tasks = [
            self._search_single(
                query,
                from_date=from_date,
                to_date=to_date,
                max_results=max_results_per_query,
            )
            for query in queries
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        seen_urls: set[str] = set()
        sources: list[Source] = []
        successful_requests = 0

        for result in results:
            if isinstance(result, BaseException):
                logger.warning("Error processing Exa query. Error: %s", result)
                continue
            successful_requests += 1
            for article in result:
                if article.url not in seen_urls:
                    seen_urls.add(article.url)
                    sources.append(article)

        usage = Usage(exa_requests=successful_requests)
        return (sources, usage)

    async def _search_single(
        self,
        query: SearchQuery,
        *,
        from_date: str | None,
        to_date: str | None,
        max_results: int,
    ) -> list[Article]:
        """Execute a single Exa search query."""
        start_date = _normalize_date(from_date) if from_date else None
        end_date = _normalize_date(to_date) if to_date else None

        response = await self._client.search(
            query.text,
            num_results=max_results,
            start_published_date=start_date,
            end_published_date=end_date,
        )

        articles: list[Article] = []
        for result in response.results:
            domain = _extract_domain(result.url)
            articles.append(
                Article(
                    url=result.url,
                    source=domain,
                    title=result.title or "",
                    published_at=result.published_date,
                    query=query,
                )
            )
        return articles


def _normalize_date(date_str: str) -> str:
    """Ensure date string includes time component for Exa API.

    Exa expects ISO 8601 with time, e.g. ``2026-01-01T00:00:00.000Z``.
    If only a date is provided, appends ``T00:00:00.000Z``.
    """
    if "T" in date_str:
        return date_str
    return f"{date_str}T00:00:00.000Z"


def _extract_domain(url: str) -> str:
    """Extract the domain from a URL, stripping 'www.' prefix."""
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname or ""
        if hostname.startswith("www."):
            hostname = hostname[4:]
        return hostname
    except Exception:
        return "unknown"
