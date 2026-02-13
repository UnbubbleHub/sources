"""Tests for protocol compliance."""

from typing import TYPE_CHECKING

import pytest

from unbubble_sources.data import NewsEvent, SearchQuery, Usage
from unbubble_sources.query.claude import ClaudeQueryGenerator
from unbubble_sources.search.x import XSearcher

if TYPE_CHECKING:
    pass


def test_claude_generator_matches_protocol() -> None:
    """Verify ClaudeQueryGenerator structurally matches the QueryGenerator protocol."""
    gen = ClaudeQueryGenerator(api_key="test")
    assert hasattr(gen, "generate")
    assert callable(gen.generate)


class MockQueryGenerator:
    """A minimal implementation to verify protocol requirements."""

    async def generate(
        self, event: NewsEvent, *, num_queries: int = 10
    ) -> tuple[list[SearchQuery], Usage]:
        return ([SearchQuery(text="mock", intent="mock")], Usage())


def test_mock_generator_satisfies_protocol() -> None:
    """Any class with the right method signature satisfies the protocol."""
    gen = MockQueryGenerator()
    assert hasattr(gen, "generate")
    # Type checkers will verify this matches QueryGenerator


def test_x_searcher_matches_source_searcher_protocol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify XSearcher structurally matches the SourceSearcher protocol."""
    monkeypatch.setenv("TWITTER_BEARER_TOKEN", "test-token")
    searcher = XSearcher()
    assert hasattr(searcher, "search")
    assert callable(searcher.search)
