"""Tests for ClaudeQueryGenerator."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from anthropic.types import TextBlock

from unbubble_sources.data import NewsEvent, SearchQuery, Usage
from unbubble_sources.query.claude import DEFAULT_SYSTEM_PROMPT, ClaudeQueryGenerator


def _make_mock_usage(input_tokens: int = 100, output_tokens: int = 50) -> MagicMock:
    """Create a mock usage object."""
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.cache_creation_input_tokens = 0
    usage.cache_read_input_tokens = 0
    return usage


@pytest.fixture
def mock_response() -> MagicMock:
    """Create a mock API response with a real TextBlock."""
    response = MagicMock()
    response.content = [
        TextBlock(
            type="text",
            text='[{"text": "query 1", "intent": "intent 1"}, {"text": "query 2", "intent": "intent 2"}]',
        )
    ]
    response.usage = _make_mock_usage()
    return response


@pytest.fixture
def generator(mock_response: MagicMock) -> ClaudeQueryGenerator:
    """Create a generator with mocked API client."""
    gen = ClaudeQueryGenerator(api_key="test-key")
    object.__setattr__(gen._client.messages, "create", AsyncMock(return_value=mock_response))
    return gen


async def test_generate_returns_search_queries(generator: ClaudeQueryGenerator) -> None:
    event = NewsEvent(description="Test event")
    queries, usage = await generator.generate(event, num_queries=2)

    assert len(queries) == 2
    assert all(isinstance(q, SearchQuery) for q in queries)
    assert queries[0].text == "query 1"
    assert queries[0].intent == "intent 1"


async def test_generate_returns_usage(generator: ClaudeQueryGenerator) -> None:
    event = NewsEvent(description="Test event")
    queries, usage = await generator.generate(event, num_queries=2)

    assert isinstance(usage, Usage)
    assert len(usage.api_calls) == 1
    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    assert usage.api_calls[0].model == "claude-haiku-4-5-20251001"


async def test_generate_calls_api_with_correct_params(
    generator: ClaudeQueryGenerator,
) -> None:
    event = NewsEvent(
        description="Test event",
        date="2026-02-01",
        context="Test context",
    )
    await generator.generate(event, num_queries=5)

    mock_create: AsyncMock = generator._client.messages.create  # type: ignore[assignment]
    call_kwargs = dict(mock_create.call_args.kwargs)
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
    assert call_kwargs["max_tokens"] == 1024
    assert "{num_queries}" not in call_kwargs["system"]  # should be formatted
    assert "5" in call_kwargs["system"]

    user_content = call_kwargs["messages"][0]["content"]
    assert "Test event" in user_content
    assert "2026-02-01" in user_content
    assert "Test context" in user_content


async def test_generate_handles_markdown_code_fences() -> None:
    """Test that markdown code fences are stripped from response."""
    gen = ClaudeQueryGenerator(api_key="test-key")
    response = MagicMock()
    response.content = [
        TextBlock(
            type="text",
            text='```json\n[{"text": "q", "intent": "i"}]\n```',
        )
    ]
    response.usage = _make_mock_usage()
    object.__setattr__(gen._client.messages, "create", AsyncMock(return_value=response))

    event = NewsEvent(description="Test")
    queries, usage = await gen.generate(event)

    assert len(queries) == 1
    assert queries[0].text == "q"


async def test_custom_system_prompt() -> None:
    """Test that custom system prompt is used."""
    custom_prompt = "Custom prompt with {num_queries} queries"
    gen = ClaudeQueryGenerator(api_key="test-key", system_prompt=custom_prompt)

    response = MagicMock()
    response.content = [
        TextBlock(
            type="text",
            text='[{"text": "q", "intent": "i"}]',
        )
    ]
    response.usage = _make_mock_usage()
    object.__setattr__(gen._client.messages, "create", AsyncMock(return_value=response))

    event = NewsEvent(description="Test")
    await gen.generate(event, num_queries=3)

    mock_create: AsyncMock = gen._client.messages.create  # type: ignore[assignment]
    call_kwargs = dict(mock_create.call_args.kwargs)
    assert call_kwargs["system"] == "Custom prompt with 3 queries"


async def test_custom_model() -> None:
    """Test that custom model is used."""
    gen = ClaudeQueryGenerator(api_key="test-key", model="claude-3-haiku-20240307")

    response = MagicMock()
    response.content = [
        TextBlock(
            type="text",
            text='[{"text": "q", "intent": "i"}]',
        )
    ]
    response.usage = _make_mock_usage()
    object.__setattr__(gen._client.messages, "create", AsyncMock(return_value=response))

    event = NewsEvent(description="Test")
    await gen.generate(event)

    mock_create: AsyncMock = gen._client.messages.create  # type: ignore[assignment]
    call_kwargs = dict(mock_create.call_args.kwargs)
    assert call_kwargs["model"] == "claude-3-haiku-20240307"


def test_default_system_prompt_has_placeholder() -> None:
    assert "{num_queries}" in DEFAULT_SYSTEM_PROMPT


def test_default_system_prompt_requests_json() -> None:
    assert "JSON" in DEFAULT_SYSTEM_PROMPT
    assert '"text"' in DEFAULT_SYSTEM_PROMPT
    assert '"intent"' in DEFAULT_SYSTEM_PROMPT
