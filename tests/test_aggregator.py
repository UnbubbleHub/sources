"""Tests for query aggregators."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import numpy as np
import pytest

from unbubble.aggregator.pca import NoOpAggregator, PCAAggregator
from unbubble.query.models import SearchQuery


class TestNoOpAggregator:
    """Tests for NoOpAggregator."""

    async def test_returns_queries_unchanged(self) -> None:
        aggregator = NoOpAggregator()
        queries = [
            SearchQuery(text="query 1", intent="intent 1"),
            SearchQuery(text="query 2", intent="intent 2"),
        ]
        result = await aggregator.aggregate(queries)
        assert result == queries

    async def test_empty_list(self) -> None:
        aggregator = NoOpAggregator()
        result = await aggregator.aggregate([])
        assert result == []


class TestPCAAggregator:
    """Tests for PCAAggregator."""

    @pytest.fixture
    def mock_embedder(self) -> MagicMock:
        """Create a mock embedder."""
        embedder = MagicMock()
        # Return embeddings that are clearly different for diversity
        embedder.embed = AsyncMock(
            return_value=np.array(
                [
                    [1.0, 0.0, 0.0],
                    [0.0, 1.0, 0.0],
                    [0.0, 0.0, 1.0],
                    [0.5, 0.5, 0.0],
                    [0.0, 0.5, 0.5],
                ],
                dtype=np.float32,
            )
        )
        return embedder

    @pytest.fixture
    def aggregator(self, mock_embedder: MagicMock, monkeypatch: pytest.MonkeyPatch) -> PCAAggregator:
        """Create an aggregator with mocked embedder."""
        agg = PCAAggregator(n_components=3)
        agg._embedder = mock_embedder
        return agg

    async def test_returns_n_components_queries(self, aggregator: PCAAggregator) -> None:
        queries = [
            SearchQuery(text=f"query {i}", intent=f"intent {i}") for i in range(5)
        ]
        result = await aggregator.aggregate(queries)
        assert len(result) == 3  # n_components

    async def test_returns_all_if_fewer_than_n_components(
        self, aggregator: PCAAggregator
    ) -> None:
        queries = [
            SearchQuery(text="query 1", intent="intent 1"),
            SearchQuery(text="query 2", intent="intent 2"),
        ]
        result = await aggregator.aggregate(queries)
        assert len(result) == 2
        assert result == queries

    async def test_returns_unique_queries(
        self, aggregator: PCAAggregator, mock_embedder: MagicMock
    ) -> None:
        queries = [
            SearchQuery(text=f"query {i}", intent=f"intent {i}") for i in range(5)
        ]
        result = await aggregator.aggregate(queries)
        # All returned queries should be unique
        assert len(result) == len(set(result))

    async def test_empty_list(self, aggregator: PCAAggregator) -> None:
        result = await aggregator.aggregate([])
        assert result == []

    async def test_single_query(
        self, aggregator: PCAAggregator, mock_embedder: MagicMock
    ) -> None:
        mock_embedder.embed = AsyncMock(
            return_value=np.array([[1.0, 0.0, 0.0]], dtype=np.float32)
        )
        queries = [SearchQuery(text="only one", intent="single")]
        result = await aggregator.aggregate(queries)
        assert result == queries


def test_aggregator_protocol_compliance() -> None:
    """Verify aggregators match the QueryAggregator protocol."""
    pca = PCAAggregator(n_components=5)
    noop = NoOpAggregator()

    assert hasattr(pca, "aggregate")
    assert callable(pca.aggregate)
    assert hasattr(noop, "aggregate")
    assert callable(noop.aggregate)
