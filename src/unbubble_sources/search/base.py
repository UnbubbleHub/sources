from typing import Protocol

from unbubble_sources.data import SearchQuery, Source, Usage


class SourceSearcher(Protocol):
    """Interface for searching sources (articles, tweets, etc.)."""

    async def search(
        self,
        queries: list[SearchQuery],
        *,
        from_date: str | None = None,
        to_date: str | None = None,
        max_results_per_query: int = 10,
    ) -> tuple[list[Source], Usage]:
        """Search for sources matching the given queries.

        Args:
            queries: List of search queries to execute.
            from_date: Start date filter (ISO format, e.g. "2026-01-01").
            to_date: End date filter (ISO format).
            max_results_per_query: Maximum sources to return per query.

        Returns:
            Tuple of (deduplicated sources, usage).
        """
        ...


# Backward compatibility alias
ArticleSearcher = SourceSearcher
