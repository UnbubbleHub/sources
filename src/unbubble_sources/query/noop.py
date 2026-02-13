"""No-op query generator that passes through the event description as-is."""

from unbubble_sources.data import NewsEvent, SearchQuery, Usage


class NoOpQueryGenerator:
    """Query generator that wraps the event description into a single SearchQuery.

    No API calls are made — the raw event description is used directly as the
    search query. This is useful for cheap pipelines that rely solely on
    free-tier searchers (GNews, X, Exa).
    """

    async def generate(
        self, event: NewsEvent, *, num_queries: int = 10
    ) -> tuple[list[SearchQuery], Usage]:
        """Return the event description as a single search query.

        The ``num_queries`` parameter is accepted for protocol compatibility
        but ignored — exactly one query is always returned.

        Args:
            event: News event to generate queries for.
            num_queries: Ignored (always returns 1 query).

        Returns:
            Tuple of (single-element query list, empty usage).
        """
        query = SearchQuery(text=event.description, intent="original query")
        return ([query], Usage())
