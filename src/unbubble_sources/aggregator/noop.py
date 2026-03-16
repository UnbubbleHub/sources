"""No-op query aggregator (no ML dependencies required)."""

from unbubble_sources.data import SearchQuery


class NoOpAggregator:
    """Pass-through aggregator that returns queries unchanged."""

    async def aggregate(self, queries: list[SearchQuery]) -> list[SearchQuery]:
        """Return queries unchanged.

        Args:
            queries: Input queries.

        Returns:
            Same queries, unchanged.
        """
        return queries
