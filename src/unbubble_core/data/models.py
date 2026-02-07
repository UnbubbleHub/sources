"""Core data models for Unbubble."""

from __future__ import annotations

from dataclasses import dataclass


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
