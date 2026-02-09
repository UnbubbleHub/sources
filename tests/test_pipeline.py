"""Tests for pipelines."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from unbubble_core.data import Article, NewsEvent, SearchQuery
from unbubble_core.pipeline.claude_e2e import ClaudeE2EPipeline
from unbubble_core.pipeline.composable import ComposablePipeline
from unbubble_core.url import extract_domain


class TestComposablePipeline:
    """Tests for ComposablePipeline."""

    @pytest.fixture
    def mock_generator(self) -> MagicMock:
        """Create a mock query generator."""
        gen = MagicMock()
        gen.generate = AsyncMock(
            return_value=[
                SearchQuery(text="query 1", intent="intent 1"),
                SearchQuery(text="query 2", intent="intent 2"),
            ]
        )
        return gen

    @pytest.fixture
    def mock_aggregator(self) -> MagicMock:
        """Create a mock aggregator that passes through."""
        agg = MagicMock()
        agg.aggregate = AsyncMock(side_effect=lambda queries: queries)
        return agg

    @pytest.fixture
    def mock_searcher(self) -> MagicMock:
        """Create a mock searcher."""
        searcher = MagicMock()
        searcher.search = AsyncMock(
            return_value=[
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
            ]
        )
        return searcher

    @pytest.fixture
    def pipeline(
        self,
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

    async def test_run_returns_articles(self, pipeline: ComposablePipeline) -> None:
        event = NewsEvent(description="Test event")
        articles = await pipeline.run(event)
        assert len(articles) == 2
        assert all(isinstance(a, Article) for a in articles)

    async def test_run_calls_generator(
        self, pipeline: ComposablePipeline, mock_generator: MagicMock
    ) -> None:
        event = NewsEvent(description="Test event")
        await pipeline.run(event)
        mock_generator.generate.assert_called_once()
        call_kwargs = mock_generator.generate.call_args.kwargs
        assert call_kwargs["num_queries"] == 5

    async def test_run_calls_aggregator(
        self, pipeline: ComposablePipeline, mock_aggregator: MagicMock
    ) -> None:
        event = NewsEvent(description="Test event")
        await pipeline.run(event)
        mock_aggregator.aggregate.assert_called_once()

    async def test_run_calls_searcher(
        self, pipeline: ComposablePipeline, mock_searcher: MagicMock
    ) -> None:
        event = NewsEvent(description="Test event")
        await pipeline.run(event)
        mock_searcher.search.assert_called_once()

    async def test_run_deduplicates_by_url(
        self,
        mock_generator: MagicMock,
        mock_aggregator: MagicMock,
    ) -> None:
        # Two searchers returning the same article
        searcher1 = MagicMock()
        searcher1.search = AsyncMock(
            return_value=[
                Article(title="Article 1", url="https://example.com/1", source="A"),
            ]
        )
        searcher2 = MagicMock()
        searcher2.search = AsyncMock(
            return_value=[
                Article(title="Article 1", url="https://example.com/1", source="B"),
            ]
        )

        pipeline = ComposablePipeline(
            generators=[mock_generator],
            aggregator=mock_aggregator,
            searchers=[searcher1, searcher2],
        )

        event = NewsEvent(description="Test event")
        articles = await pipeline.run(event)
        assert len(articles) == 1  # Deduplicated

    async def test_run_handles_generator_failure(
        self,
        mock_aggregator: MagicMock,
        mock_searcher: MagicMock,
    ) -> None:
        failing_gen = MagicMock()
        failing_gen.generate = AsyncMock(side_effect=Exception("API error"))

        working_gen = MagicMock()
        working_gen.generate = AsyncMock(
            return_value=[SearchQuery(text="query", intent="intent")]
        )

        pipeline = ComposablePipeline(
            generators=[failing_gen, working_gen],
            aggregator=mock_aggregator,
            searchers=[mock_searcher],
        )

        event = NewsEvent(description="Test event")
        articles = await pipeline.run(event)
        # Should still return articles from working generator
        assert len(articles) == 2

    async def test_run_returns_empty_if_no_queries(
        self,
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
        articles = await pipeline.run(event)
        assert articles == []


class TestClaudeE2EPipeline:
    """Tests for ClaudeE2EPipeline."""

    @pytest.fixture
    def mock_response(self) -> MagicMock:
        """Create a mock API response."""
        from anthropic.types import WebSearchResultBlock, WebSearchToolResultBlock

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

        # Make isinstance checks work
        response = MagicMock()
        response.content = [tool_result]
        return response

    @pytest.fixture
    def pipeline(self, mock_response: MagicMock) -> ClaudeE2EPipeline:
        """Create a pipeline with mocked client."""
        p = ClaudeE2EPipeline(api_key="test-key", target_articles=10)
        object.__setattr__(p._client.messages, "create", AsyncMock(return_value=mock_response))
        return p

    async def test_run_calls_api_with_web_search(
        self, pipeline: ClaudeE2EPipeline
    ) -> None:
        event = NewsEvent(description="Test event")
        await pipeline.run(event)

        mock_create: AsyncMock = pipeline._client.messages.create  # type: ignore[assignment]
        call_kwargs = dict(mock_create.call_args.kwargs)
        assert "tools" in call_kwargs
        assert call_kwargs["tools"][0]["type"] == "web_search_20250305"

    async def test_run_includes_event_in_prompt(
        self, pipeline: ClaudeE2EPipeline
    ) -> None:
        event = NewsEvent(
            description="Test event",
            date="2026-02-01",
            context="Test context",
        )
        await pipeline.run(event)

        mock_create: AsyncMock = pipeline._client.messages.create  # type: ignore[assignment]
        call_kwargs = dict(mock_create.call_args.kwargs)
        user_content = call_kwargs["messages"][0]["content"]
        assert "Test event" in user_content
        assert "2026-02-01" in user_content
        assert "Test context" in user_content

    def test_extract_domain(self, pipeline: ClaudeE2EPipeline) -> None:
        # Test the centralized extract_domain function
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
