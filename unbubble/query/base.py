from __future__ import annotations

from typing import Protocol

from unbubble.query.models import NewsEvent, SearchQuery


class QueryGenerator(Protocol):
    """Interface for generating diverse search queries from a news event."""

    async def generate(self, event: NewsEvent, *, num_queries: int = 10) -> list[SearchQuery]: ...
