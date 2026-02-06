"""Tests for GNewsSearcher."""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest

from unbubble.query.models import Article, SearchQuery
from unbubble.search.gnews import GNewsSearcher


class TestGNewsSearcher:
    """Tests for GNewsSearcher."""

    @pytest.fixture
    def mock_response_data(self) -> dict:
        """Sample GNews API response."""
        return {
            "totalArticles": 2,
            "articles": [
                {
                    "title": "Article 1",
                    "url": "https://example.com/article1",
                    "source": {"name": "Example News"},
                    "publishedAt": "2026-02-01T10:00:00Z",
                    "description": "Description 1",
                },
                {
                    "title": "Article 2",
                    "url": "https://example.com/article2",
                    "source": {"name": "Other News"},
                    "publishedAt": "2026-02-01T11:00:00Z",
                    "description": "Description 2",
                },
            ],
        }

    @pytest.fixture
    def searcher(self) -> GNewsSearcher:
        """Create a searcher with test API key."""
        return GNewsSearcher(api_key="test-key")

    def test_init_requires_api_key(self, monkeypatch: pytest.MonkeyPatch):
        """Should raise if no API key provided."""
        monkeypatch.delenv("GNEWS_API_KEY", raising=False)
        with pytest.raises(ValueError, match="API key required"):
            GNewsSearcher()

    def test_init_uses_env_var(self, monkeypatch: pytest.MonkeyPatch):
        """Should use GNEWS_API_KEY env var if no key passed."""
        monkeypatch.setenv("GNEWS_API_KEY", "env-key")
        searcher = GNewsSearcher()
        assert searcher._api_key == "env-key"

    async def test_search_returns_articles(
        self,
        searcher: GNewsSearcher,
        mock_response_data: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Should return list of Article objects."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        async def mock_get(*args, **kwargs):
            return mock_response

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        queries = [SearchQuery(text="test query", intent="test intent")]
        articles = await searcher.search(queries)

        assert len(articles) == 2
        assert all(isinstance(a, Article) for a in articles)
        assert articles[0].title == "Article 1"
        assert articles[0].source == "Example News"
        assert articles[0].query == queries[0]

    async def test_search_deduplicates_by_url(
        self,
        searcher: GNewsSearcher,
        mock_response_data: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Should deduplicate articles with same URL across queries."""
        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        async def mock_get(*args, **kwargs):
            return mock_response

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        # Two queries that return the same articles
        queries = [
            SearchQuery(text="query 1", intent="intent 1"),
            SearchQuery(text="query 2", intent="intent 2"),
        ]
        articles = await searcher.search(queries)

        # Should have 2 articles, not 4 (deduplicated)
        assert len(articles) == 2

    async def test_search_passes_date_params(
        self,
        searcher: GNewsSearcher,
        mock_response_data: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Should pass from_date and to_date to API."""
        captured_params: dict = {}

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        async def mock_get(self, url, params=None):
            captured_params.update(params or {})
            return mock_response

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        queries = [SearchQuery(text="test", intent="test")]
        await searcher.search(
            queries,
            from_date="2026-01-01",
            to_date="2026-02-01",
            max_results_per_query=10,
        )

        assert captured_params["from"] == "2026-01-01"
        assert captured_params["to"] == "2026-02-01"
        assert captured_params["max"] == 10
        assert captured_params["apikey"] == "test-key"

    async def test_search_handles_failed_queries(
        self,
        searcher: GNewsSearcher,
        mock_response_data: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Should skip failed queries and return results from successful ones."""
        call_count = 0

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        async def mock_get(self, url, params=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.HTTPError("API error")
            return mock_response

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        queries = [
            SearchQuery(text="failing query", intent="will fail"),
            SearchQuery(text="working query", intent="will work"),
        ]
        articles = await searcher.search(queries)

        # Should have articles from the second query only
        assert len(articles) == 2

    async def test_search_caps_max_results(
        self,
        searcher: GNewsSearcher,
        mock_response_data: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Should cap max_results at 100 (GNews limit)."""
        captured_params: dict = {}

        mock_response = MagicMock()
        mock_response.json.return_value = mock_response_data
        mock_response.raise_for_status = MagicMock()

        async def mock_get(self, url, params=None):
            captured_params.update(params or {})
            return mock_response

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        queries = [SearchQuery(text="test", intent="test")]
        await searcher.search(queries, max_results_per_query=200)

        assert captured_params["max"] == 100  # Capped at 100


def test_article_dataclass():
    """Test Article dataclass creation."""
    query = SearchQuery(text="test", intent="test")
    article = Article(
        title="Test Article",
        url="https://example.com",
        source="Test Source",
        published_at="2026-02-01",
        description="Test description",
        query=query,
    )
    assert article.title == "Test Article"
    assert article.query == query
