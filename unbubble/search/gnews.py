from __future__ import annotations

import asyncio
import os

import httpx

from unbubble.query.models import Article, SearchQuery

GNEWS_API_URL = "https://gnews.io/api/v4/search"


class GNewsSearcher:
    """Search for news articles using the GNews API.

    Args:
        api_key: GNews API key (defaults to GNEWS_API_KEY env var).
        lang: Language code for results (default: "en").
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        lang: str = "en",
    ) -> None:
        self._api_key = api_key or os.environ.get("GNEWS_API_KEY")
        if not self._api_key:
            raise ValueError("GNews API key required. Pass api_key or set GNEWS_API_KEY env var.")
        self._lang = lang

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
            from_date: Start date filter (ISO format, e.g. "2026-01-01").
            to_date: End date filter (ISO format).
            max_results_per_query: Maximum articles to return per query (max 100).

        Returns:
            Deduplicated list of articles found across all queries.
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            tasks = [
                self._search_single(
                    client,
                    query,
                    from_date=from_date,
                    to_date=to_date,
                    max_results=max_results_per_query,
                )
                for query in queries
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten and deduplicate by URL
        seen_urls: set[str] = set()
        articles: list[Article] = []
        for result in results:
            if isinstance(result, BaseException):
                # Log or handle errors; for now skip failed queries
                continue
            # result is list[Article] here
            for article in result:
                if article.url not in seen_urls:
                    seen_urls.add(article.url)
                    articles.append(article)

        return articles

    async def _search_single(
        self,
        client: httpx.AsyncClient,
        query: SearchQuery,
        *,
        from_date: str | None,
        to_date: str | None,
        max_results: int,
    ) -> list[Article]:
        """Execute a single search query."""
        params: dict[str, str | int] = {
            "q": query.text,
            "lang": self._lang,
            "max": min(max_results, 100),  # GNews max is 100
            "apikey": self._api_key,  # type: ignore[dict-item]
        }
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date

        response = await client.get(GNEWS_API_URL, params=params)
        response.raise_for_status()
        data = response.json()

        articles: list[Article] = []
        for item in data.get("articles", []):
            articles.append(
                Article(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    source=item.get("source", {}).get("name", "Unknown"),
                    published_at=item.get("publishedAt"),
                    description=item.get("description"),
                    query=query,
                )
            )
        return articles
