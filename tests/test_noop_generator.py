"""Tests for NoOpQueryGenerator."""

from unbubble_sources.data import NewsEvent, SearchQuery, Usage
from unbubble_sources.query.noop import NoOpQueryGenerator


async def test_generate_returns_single_query() -> None:
    """Should return exactly one SearchQuery wrapping the event description."""
    gen = NoOpQueryGenerator()
    event = NewsEvent(description="Climate summit negotiations")
    queries, usage = await gen.generate(event)

    assert len(queries) == 1
    assert isinstance(queries[0], SearchQuery)
    assert queries[0].text == "Climate summit negotiations"
    assert queries[0].intent == "original query"


async def test_generate_returns_empty_usage() -> None:
    """Should return a zero-cost Usage object."""
    gen = NoOpQueryGenerator()
    event = NewsEvent(description="Test event")
    queries, usage = await gen.generate(event)

    assert isinstance(usage, Usage)
    assert len(usage.api_calls) == 0
    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.estimated_cost == 0.0


async def test_generate_ignores_num_queries() -> None:
    """The num_queries parameter is accepted but always returns 1 query."""
    gen = NoOpQueryGenerator()
    event = NewsEvent(description="Test event")
    queries, _ = await gen.generate(event, num_queries=50)

    assert len(queries) == 1


def test_noop_generator_matches_protocol() -> None:
    """Verify NoOpQueryGenerator structurally matches the QueryGenerator protocol."""
    gen = NoOpQueryGenerator()
    assert hasattr(gen, "generate")
    assert callable(gen.generate)
