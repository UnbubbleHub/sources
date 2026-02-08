"""Query aggregator protocol."""

from typing import Protocol

from unbubble_core.data import SearchQuery


class QueryAggregator(Protocol):
    """Interface for aggregating/reducing search queries."""

    async def aggregate(self, queries: list[SearchQuery]) -> list[SearchQuery]:
        """Aggregate queries to reduce redundancy while maintaining diversity.

        Args:
            queries: Input queries from one or more generators.

        Returns:
            Reduced list of diverse queries.
        """
        ...
