"""Tests for the QueryGenerator protocol."""

from __future__ import annotations

from typing import TYPE_CHECKING

from unbubble.query.claude import ClaudeQueryGenerator
from unbubble.query.models import NewsEvent, SearchQuery

if TYPE_CHECKING:
    pass


def test_claude_generator_matches_protocol():
    """Verify ClaudeQueryGenerator structurally matches the QueryGenerator protocol."""
    # This is a compile-time check via type annotations, but we can also verify
    # that the required method exists with the right signature
    gen = ClaudeQueryGenerator(api_key="test")
    assert hasattr(gen, "generate")
    assert callable(gen.generate)


class MockQueryGenerator:
    """A minimal implementation to verify protocol requirements."""

    async def generate(self, event: NewsEvent, *, num_queries: int = 10) -> list[SearchQuery]:
        return [SearchQuery(text="mock", intent="mock")]


def test_mock_generator_satisfies_protocol():
    """Any class with the right method signature satisfies the protocol."""
    gen = MockQueryGenerator()
    assert hasattr(gen, "generate")
    # Type checkers will verify this matches QueryGenerator
