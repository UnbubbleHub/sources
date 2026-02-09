"""Tests for query aggregators."""

from unittest.mock import MagicMock

import numpy as np
import pytest

from unbubble_sources.aggregator.pca import NoOpAggregator, PCAAggregator
from unbubble_sources.data import SearchQuery

# -- NoOpAggregator tests --


async def test_noop_returns_queries_unchanged() -> None:
    aggregator = NoOpAggregator()
    queries = [
        SearchQuery(text="query 1", intent="intent 1"),
        SearchQuery(text="query 2", intent="intent 2"),
    ]
    result = await aggregator.aggregate(queries)
    assert result == queries


async def test_noop_empty_list() -> None:
    aggregator = NoOpAggregator()
    result = await aggregator.aggregate([])
    assert result == []


# -- PCAAggregator tests --


@pytest.fixture
def mock_embedder() -> MagicMock:
    """Create a mock embedder."""
    embedder = MagicMock()
    embedder.embed.return_value = np.array(
        [
            [1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 0.0, 1.0],
            [0.5, 0.5, 0.0],
            [0.0, 0.5, 0.5],
        ],
        dtype=np.float32,
    )
    return embedder


@pytest.fixture
def pca_aggregator(mock_embedder: MagicMock) -> PCAAggregator:
    """Create an aggregator with mocked embedder."""
    agg = PCAAggregator(n_components=3)
    agg._embedder = mock_embedder
    return agg


async def test_pca_returns_n_components_queries(pca_aggregator: PCAAggregator) -> None:
    queries = [
        SearchQuery(text=f"query {i}", intent=f"intent {i}") for i in range(5)
    ]
    result = await pca_aggregator.aggregate(queries)
    assert len(result) == 3  # n_components


async def test_pca_returns_all_if_fewer_than_n_components(
    pca_aggregator: PCAAggregator,
) -> None:
    queries = [
        SearchQuery(text="query 1", intent="intent 1"),
        SearchQuery(text="query 2", intent="intent 2"),
    ]
    result = await pca_aggregator.aggregate(queries)
    assert len(result) == 2
    assert result == queries


async def test_pca_returns_unique_queries(
    pca_aggregator: PCAAggregator,
) -> None:
    queries = [
        SearchQuery(text=f"query {i}", intent=f"intent {i}") for i in range(5)
    ]
    result = await pca_aggregator.aggregate(queries)
    assert len(result) == len(set(result))


async def test_pca_empty_list(pca_aggregator: PCAAggregator) -> None:
    result = await pca_aggregator.aggregate([])
    assert result == []


async def test_pca_single_query(
    pca_aggregator: PCAAggregator, mock_embedder: MagicMock
) -> None:
    mock_embedder.embed.return_value = np.array(
        [[1.0, 0.0, 0.0]], dtype=np.float32
    )
    queries = [SearchQuery(text="only one", intent="single")]
    result = await pca_aggregator.aggregate(queries)
    assert result == queries


def test_aggregator_protocol_compliance() -> None:
    """Verify aggregators match the QueryAggregator protocol."""
    pca = PCAAggregator(n_components=5)
    noop = NoOpAggregator()

    assert hasattr(pca, "aggregate")
    assert callable(pca.aggregate)
    assert hasattr(noop, "aggregate")
    assert callable(noop.aggregate)
