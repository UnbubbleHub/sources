"""Tests for pipelines."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from anthropic.types import WebSearchResultBlock, WebSearchToolResultBlock

from unbubble_sources.data import Article, NewsEvent, SearchQuery, Usage
from unbubble_sources.pipeline.claude_e2e import ClaudeE2EPipeline
from unbubble_sources.pipeline.composable import ComposablePipeline
from unbubble_sources.url import extract_domain

# -- Helpers --


def _make_mock_usage(
    input_tokens: int = 200,
    output_tokens: int = 100,
    web_search_requests: int = 1,
) -> MagicMock:
    """Create a mock usage object with server_tool_use."""
    usage = MagicMock()
    usage.input_tokens = input_tokens
    usage.output_tokens = output_tokens
    usage.cache_creation_input_tokens = 0
    usage.cache_read_input_tokens = 0
    server_tool_use = MagicMock()
    server_tool_use.web_search_requests = web_search_requests
    usage.server_tool_use = server_tool_use
    return usage


# -- Composable pipeline fixtures --


@pytest.fixture
def mock_generator() -> MagicMock:
    """Create a mock query generator."""
    gen = MagicMock()
    gen.generate = AsyncMock(
        return_value=(
            [
                SearchQuery(text="query 1", intent="intent 1"),
                SearchQuery(text="query 2", intent="intent 2"),
            ],
            Usage(),
        )
    )
    return gen


@pytest.fixture
def mock_aggregator() -> MagicMock:
    """Create a mock aggregator that passes through."""
    agg = MagicMock()
    agg.aggregate = AsyncMock(side_effect=lambda queries: queries)
    return agg


@pytest.fixture
def mock_searcher() -> MagicMock:
    """Create a mock searcher."""
    searcher = MagicMock()
    searcher.search = AsyncMock(
        return_value=(
            [
                Article(
                    title="Article 1",
                    url="https://example.com/1",
                    source="Example",
                ),
                Article(
                    title="Article 2",
                    url="https://example.com/2",
                    source="Example",
                ),
            ],
            Usage(),
        )
    )
    return searcher


@pytest.fixture
def composable_pipeline(
    mock_generator: MagicMock,
    mock_aggregator: MagicMock,
    mock_searcher: MagicMock,
) -> ComposablePipeline:
    """Create a pipeline with mocked components."""
    return ComposablePipeline(
        generators=[mock_generator],
        aggregator=mock_aggregator,
        searchers=[mock_searcher],
        num_queries_per_generator=5,
        max_results_per_searcher=10,
    )


# -- Composable pipeline tests --


async def test_composable_run_returns_articles(
    composable_pipeline: ComposablePipeline,
) -> None:
    event = NewsEvent(description="Test event")
    articles, usage = await composable_pipeline.run(event)
    assert len(articles) == 2
    assert all(isinstance(a, Article) for a in articles)


async def test_composable_run_returns_usage(
    composable_pipeline: ComposablePipeline,
) -> None:
    event = NewsEvent(description="Test event")
    articles, usage = await composable_pipeline.run(event)
    assert isinstance(usage, Usage)


async def test_composable_run_calls_generator(
    composable_pipeline: ComposablePipeline, mock_generator: MagicMock
) -> None:
    event = NewsEvent(description="Test event")
    await composable_pipeline.run(event)
    mock_generator.generate.assert_called_once()
    call_kwargs = mock_generator.generate.call_args.kwargs
    assert call_kwargs["num_queries"] == 5


async def test_composable_run_calls_aggregator(
    composable_pipeline: ComposablePipeline, mock_aggregator: MagicMock
) -> None:
    event = NewsEvent(description="Test event")
    await composable_pipeline.run(event)
    mock_aggregator.aggregate.assert_called_once()


async def test_composable_run_calls_searcher(
    composable_pipeline: ComposablePipeline, mock_searcher: MagicMock
) -> None:
    event = NewsEvent(description="Test event")
    await composable_pipeline.run(event)
    mock_searcher.search.assert_called_once()


async def test_composable_run_deduplicates_by_url(
    mock_generator: MagicMock,
    mock_aggregator: MagicMock,
) -> None:
    searcher1 = MagicMock()
    searcher1.search = AsyncMock(
        return_value=(
            [Article(title="Article 1", url="https://example.com/1", source="A")],
            Usage(),
        )
    )
    searcher2 = MagicMock()
    searcher2.search = AsyncMock(
        return_value=(
            [Article(title="Article 1", url="https://example.com/1", source="B")],
            Usage(),
        )
    )

    pipeline = ComposablePipeline(
        generators=[mock_generator],
        aggregator=mock_aggregator,
        searchers=[searcher1, searcher2],
    )

    event = NewsEvent(description="Test event")
    articles, usage = await pipeline.run(event)
    assert len(articles) == 1  # Deduplicated


async def test_composable_run_handles_generator_failure(
    mock_aggregator: MagicMock,
    mock_searcher: MagicMock,
) -> None:
    failing_gen = MagicMock()
    failing_gen.generate = AsyncMock(side_effect=Exception("API error"))

    working_gen = MagicMock()
    working_gen.generate = AsyncMock(
        return_value=(
            [SearchQuery(text="query", intent="intent")],
            Usage(),
        )
    )

    pipeline = ComposablePipeline(
        generators=[failing_gen, working_gen],
        aggregator=mock_aggregator,
        searchers=[mock_searcher],
    )

    event = NewsEvent(description="Test event")
    articles, usage = await pipeline.run(event)
    assert len(articles) == 2


async def test_composable_run_returns_empty_if_no_queries(
    mock_aggregator: MagicMock,
    mock_searcher: MagicMock,
) -> None:
    failing_gen = MagicMock()
    failing_gen.generate = AsyncMock(side_effect=Exception("API error"))

    pipeline = ComposablePipeline(
        generators=[failing_gen],
        aggregator=mock_aggregator,
        searchers=[mock_searcher],
    )

    event = NewsEvent(description="Test event")
    articles, usage = await pipeline.run(event)
    assert articles == []
    assert isinstance(usage, Usage)


# -- Claude E2E pipeline fixtures --


@pytest.fixture
def e2e_mock_response() -> MagicMock:
    """Create a mock API response."""
    result = WebSearchResultBlock(
        type="web_search_result",
        url="https://example.com/article",
        title="Test Article",
        encrypted_content="encrypted",
        page_age="February 1, 2026",
    )

    tool_result = MagicMock(spec=WebSearchToolResultBlock)
    tool_result.type = "web_search_tool_result"
    tool_result.content = [result]

    response = MagicMock()
    response.content = [tool_result]
    response.usage = _make_mock_usage()
    return response


@pytest.fixture
def e2e_pipeline(e2e_mock_response: MagicMock) -> ClaudeE2EPipeline:
    """Create a pipeline with mocked client."""
    p = ClaudeE2EPipeline(api_key="test-key", target_articles=10)
    object.__setattr__(p._client.messages, "create", AsyncMock(return_value=e2e_mock_response))
    return p


# -- Claude E2E pipeline tests --


async def test_e2e_run_calls_api_with_web_search(
    e2e_pipeline: ClaudeE2EPipeline,
) -> None:
    event = NewsEvent(description="Test event")
    await e2e_pipeline.run(event)

    mock_create: AsyncMock = e2e_pipeline._client.messages.create  # type: ignore[assignment]
    call_kwargs = dict(mock_create.call_args.kwargs)
    assert "tools" in call_kwargs
    assert call_kwargs["tools"][0]["type"] == "web_search_20250305"


async def test_e2e_run_returns_usage(
    e2e_pipeline: ClaudeE2EPipeline,
) -> None:
    event = NewsEvent(description="Test event")
    articles, usage = await e2e_pipeline.run(event)

    assert isinstance(usage, Usage)
    assert len(usage.api_calls) == 1
    assert usage.input_tokens == 200
    assert usage.output_tokens == 100
    assert usage.web_searches == 1


async def test_e2e_run_includes_event_in_prompt(
    e2e_pipeline: ClaudeE2EPipeline,
) -> None:
    event = NewsEvent(
        description="Test event",
        date="2026-02-01",
        context="Test context",
    )
    await e2e_pipeline.run(event)

    mock_create: AsyncMock = e2e_pipeline._client.messages.create  # type: ignore[assignment]
    call_kwargs = dict(mock_create.call_args.kwargs)
    user_content = call_kwargs["messages"][0]["content"]
    assert "Test event" in user_content
    assert "2026-02-01" in user_content
    assert "Test context" in user_content


def test_e2e_extract_domain() -> None:
    assert extract_domain("https://www.example.com/path") == "example.com"
    assert extract_domain("https://news.example.com") == "news.example.com"
    assert extract_domain("invalid") == "Unknown"


def test_pipeline_protocol_compliance() -> None:
    """Verify pipelines match the Pipeline protocol."""
    composable = ComposablePipeline(
        generators=[],
        aggregator=MagicMock(),
        searchers=[],
    )
    e2e = ClaudeE2EPipeline(api_key="test")

    assert hasattr(composable, "run")
    assert callable(composable.run)
    assert hasattr(e2e, "run")
    assert callable(e2e.run)
