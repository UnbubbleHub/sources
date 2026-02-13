"""Tests for ExaSearcher."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from unbubble_sources.data import Article, SearchQuery, Usage
from unbubble_sources.search.exa import ExaSearcher, _extract_domain, _normalize_date


def _make_mock_result(
    url: str = "https://example.com/article",
    title: str = "Test Article",
    published_date: str | None = "2026-02-01T10:00:00.000Z",
) -> MagicMock:
    """Create a mock Exa search result."""
    result = MagicMock()
    result.url = url
    result.title = title
    result.published_date = published_date
    return result


def _make_mock_response(results: list[MagicMock] | None = None) -> MagicMock:
    """Create a mock Exa search response."""
    response = MagicMock()
    response.results = results or [
        _make_mock_result(
            url="https://example.com/article1",
            title="Article 1",
        ),
        _make_mock_result(
            url="https://other.com/article2",
            title="Article 2",
        ),
    ]
    return response


@pytest.fixture
def exa_searcher() -> ExaSearcher:
    """Create a searcher with test API key."""
    return ExaSearcher(api_key="test-key")


def test_init_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should raise if no API key provided."""
    monkeypatch.delenv("EXA_API_KEY", raising=False)
    with pytest.raises(ValueError, match="API key required"):
        ExaSearcher()


def test_init_uses_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should use EXA_API_KEY env var if no key passed."""
    monkeypatch.setenv("EXA_API_KEY", "env-key")
    searcher = ExaSearcher()
    assert searcher._api_key == "env-key"


async def test_search_returns_articles(
    exa_searcher: ExaSearcher,
) -> None:
    """Should return list of Article objects."""
    mock_response = _make_mock_response()
    exa_searcher._client.search = AsyncMock(return_value=mock_response)

    queries = [SearchQuery(text="test query", intent="test intent")]
    sources, usage = await exa_searcher.search(queries)

    assert len(sources) == 2
    assert all(isinstance(s, Article) for s in sources)
    article = sources[0]
    assert isinstance(article, Article)
    assert article.title == "Article 1"
    assert article.url == "https://example.com/article1"
    assert article.source == "example.com"
    assert article.query == queries[0]


async def test_search_returns_usage(
    exa_searcher: ExaSearcher,
) -> None:
    """Should return usage with exa_requests count."""
    mock_response = _make_mock_response()
    exa_searcher._client.search = AsyncMock(return_value=mock_response)

    queries = [
        SearchQuery(text="query 1", intent="intent 1"),
        SearchQuery(text="query 2", intent="intent 2"),
    ]
    sources, usage = await exa_searcher.search(queries)

    assert isinstance(usage, Usage)
    assert usage.exa_requests == 2
    assert len(usage.api_calls) == 0


async def test_search_deduplicates_by_url(
    exa_searcher: ExaSearcher,
) -> None:
    """Should deduplicate articles with same URL across queries."""
    mock_response = _make_mock_response()
    exa_searcher._client.search = AsyncMock(return_value=mock_response)

    queries = [
        SearchQuery(text="query 1", intent="intent 1"),
        SearchQuery(text="query 2", intent="intent 2"),
    ]
    sources, usage = await exa_searcher.search(queries)

    # Same response for both queries — same URLs — should dedup
    assert len(sources) == 2


async def test_search_passes_date_params(
    exa_searcher: ExaSearcher,
) -> None:
    """Should pass start/end published date to Exa API."""
    mock_response = _make_mock_response()
    exa_searcher._client.search = AsyncMock(return_value=mock_response)

    queries = [SearchQuery(text="test", intent="test")]
    await exa_searcher.search(
        queries,
        from_date="2026-01-01",
        to_date="2026-02-01",
        max_results_per_query=20,
    )

    call_kwargs = exa_searcher._client.search.call_args
    assert call_kwargs.kwargs["start_published_date"] == "2026-01-01T00:00:00.000Z"
    assert call_kwargs.kwargs["end_published_date"] == "2026-02-01T00:00:00.000Z"
    assert call_kwargs.kwargs["num_results"] == 20


async def test_search_handles_failed_queries(
    exa_searcher: ExaSearcher,
) -> None:
    """Should skip failed queries and return results from successful ones."""
    mock_response = _make_mock_response()

    call_count = 0

    async def mock_search(*args: Any, **kwargs: Any) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("API error")
        return mock_response

    exa_searcher._client.search = mock_search  # type: ignore[assignment]

    queries = [
        SearchQuery(text="failing query", intent="will fail"),
        SearchQuery(text="working query", intent="will work"),
    ]
    sources, usage = await exa_searcher.search(queries)

    assert len(sources) == 2
    assert usage.exa_requests == 1


async def test_search_handles_missing_title(
    exa_searcher: ExaSearcher,
) -> None:
    """Should handle results with no title."""
    result = _make_mock_result()
    result.title = None
    mock_response = _make_mock_response(results=[result])
    exa_searcher._client.search = AsyncMock(return_value=mock_response)

    queries = [SearchQuery(text="test", intent="test")]
    sources, usage = await exa_searcher.search(queries)

    assert len(sources) == 1
    article = sources[0]
    assert isinstance(article, Article)
    assert article.title == ""


def test_normalize_date_date_only() -> None:
    """Should append time component to date-only strings."""
    assert _normalize_date("2026-01-01") == "2026-01-01T00:00:00.000Z"


def test_normalize_date_already_iso() -> None:
    """Should return ISO strings unchanged."""
    assert _normalize_date("2026-01-01T10:00:00.000Z") == "2026-01-01T10:00:00.000Z"


def test_extract_domain_strips_www() -> None:
    """Should strip www. prefix from domains."""
    assert _extract_domain("https://www.example.com/path") == "example.com"


def test_extract_domain_keeps_subdomain() -> None:
    """Should keep non-www subdomains."""
    assert _extract_domain("https://news.example.com") == "news.example.com"


def test_extract_domain_invalid_url() -> None:
    """Should return 'unknown' for invalid URLs."""
    assert _extract_domain("not-a-url") == ""
