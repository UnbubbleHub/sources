from typing import Protocol

from unbubble_sources.data import NewsEvent, SearchQuery, Usage


class QueryGenerator(Protocol):
    """Interface for generating diverse search queries from a news event."""

    async def generate(
        self, event: NewsEvent, *, num_queries: int = 10
    ) -> tuple[list[SearchQuery], Usage]: ...
