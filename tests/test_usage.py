"""Tests for Usage and APICallUsage data models."""

from unbubble_sources.data import APICallUsage, Usage


def test_api_call_usage_creation() -> None:
    call = APICallUsage(
        model="claude-haiku-4-5-20251001",
        input_tokens=100,
        output_tokens=50,
        cache_creation_input_tokens=10,
        cache_read_input_tokens=5,
        web_searches=1,
    )
    assert call.model == "claude-haiku-4-5-20251001"
    assert call.input_tokens == 100
    assert call.output_tokens == 50
    assert call.web_searches == 1


def test_api_call_usage_defaults() -> None:
    call = APICallUsage(model="test-model")
    assert call.input_tokens == 0
    assert call.output_tokens == 0
    assert call.cache_creation_input_tokens == 0
    assert call.cache_read_input_tokens == 0
    assert call.web_searches == 0


def test_api_call_usage_is_frozen() -> None:
    call = APICallUsage(model="test", input_tokens=10)
    try:
        call.input_tokens = 20  # type: ignore[misc]
        raise AssertionError("Should have raised FrozenInstanceError")
    except AttributeError:
        pass


def test_usage_empty() -> None:
    usage = Usage()
    assert usage.input_tokens == 0
    assert usage.output_tokens == 0
    assert usage.cache_creation_input_tokens == 0
    assert usage.cache_read_input_tokens == 0
    assert usage.web_searches == 0
    assert usage.gnews_requests == 0
    assert len(usage.api_calls) == 0


def test_usage_aggregates_from_api_calls() -> None:
    usage = Usage(
        api_calls=[
            APICallUsage(model="m1", input_tokens=100, output_tokens=50, web_searches=1),
            APICallUsage(model="m2", input_tokens=200, output_tokens=75, web_searches=2),
        ],
        gnews_requests=3,
    )
    assert usage.input_tokens == 300
    assert usage.output_tokens == 125
    assert usage.web_searches == 3
    assert usage.gnews_requests == 3


def test_usage_add() -> None:
    u1 = Usage(
        api_calls=[APICallUsage(model="m1", input_tokens=100)],
        gnews_requests=1,
    )
    u2 = Usage(
        api_calls=[APICallUsage(model="m2", input_tokens=200)],
        gnews_requests=2,
    )
    combined = u1 + u2

    assert len(combined.api_calls) == 2
    assert combined.input_tokens == 300
    assert combined.gnews_requests == 3
    # Original objects unchanged
    assert len(u1.api_calls) == 1
    assert len(u2.api_calls) == 1


def test_usage_iadd() -> None:
    u1 = Usage(
        api_calls=[APICallUsage(model="m1", input_tokens=100)],
        gnews_requests=1,
    )
    u2 = Usage(
        api_calls=[APICallUsage(model="m2", input_tokens=200)],
        gnews_requests=2,
    )
    u1 += u2

    assert len(u1.api_calls) == 2
    assert u1.input_tokens == 300
    assert u1.gnews_requests == 3


def test_usage_add_empty() -> None:
    u1 = Usage(
        api_calls=[APICallUsage(model="m1", input_tokens=100)],
    )
    u2 = Usage()
    combined = u1 + u2

    assert len(combined.api_calls) == 1
    assert combined.input_tokens == 100
    assert combined.gnews_requests == 0


def test_usage_cache_token_aggregation() -> None:
    usage = Usage(
        api_calls=[
            APICallUsage(
                model="m1",
                cache_creation_input_tokens=50,
                cache_read_input_tokens=30,
            ),
            APICallUsage(
                model="m2",
                cache_creation_input_tokens=100,
                cache_read_input_tokens=70,
            ),
        ],
    )
    assert usage.cache_creation_input_tokens == 150
    assert usage.cache_read_input_tokens == 100
