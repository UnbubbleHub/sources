"""Query aggregator protocol."""

from __future__ import annotations

from typing import Protocol

from unbubble.query.models import SearchQuery


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
