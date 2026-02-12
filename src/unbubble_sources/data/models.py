"""Core data models for Unbubble."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NewsEvent:
    """A news event or factual claim to investigate."""

    description: str
    date: str | None = None
    context: str | None = None


@dataclass(frozen=True)
class SearchQuery:
    """A search query generated from a news event."""

    text: str
    intent: str


@dataclass(frozen=True)
class Article:
    """A news article retrieved from search."""

    title: str
    url: str
    source: str
    published_at: str | None = None
    description: str | None = None
    query: SearchQuery | None = None  # the query that found this article


@dataclass(frozen=True)
class APICallUsage:
    """Usage from a single API call — carries model info for price lookup."""

    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    web_searches: int = 0


@dataclass
class Usage:
    """Accumulated API usage across pipeline components."""

    api_calls: list[APICallUsage] = field(default_factory=list)
    gnews_requests: int = 0
    estimated_cost: float = 0.0

    @property
    def input_tokens(self) -> int:
        return sum(c.input_tokens for c in self.api_calls)

    @property
    def output_tokens(self) -> int:
        return sum(c.output_tokens for c in self.api_calls)

    @property
    def cache_creation_input_tokens(self) -> int:
        return sum(c.cache_creation_input_tokens for c in self.api_calls)

    @property
    def cache_read_input_tokens(self) -> int:
        return sum(c.cache_read_input_tokens for c in self.api_calls)

    @property
    def web_searches(self) -> int:
        return sum(c.web_searches for c in self.api_calls)

    def __add__(self, other: Usage) -> Usage:
        return Usage(
            api_calls=self.api_calls + other.api_calls,
            gnews_requests=self.gnews_requests + other.gnews_requests,
            estimated_cost=self.estimated_cost + other.estimated_cost,
        )

    def __iadd__(self, other: Usage) -> Usage:
        self.api_calls.extend(other.api_calls)
        self.gnews_requests += other.gnews_requests
        self.estimated_cost += other.estimated_cost
        return self
