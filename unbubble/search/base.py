from __future__ import annotations

from typing import Protocol

from unbubble.data import Article, SearchQuery


class ArticleSearcher(Protocol):
    """Interface for searching news articles."""

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
            max_results_per_query: Maximum articles to return per query.

        Returns:
            Deduplicated list of articles found across all queries.
        """
        ...
