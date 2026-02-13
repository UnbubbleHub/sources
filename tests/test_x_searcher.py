"""Tests for XSearcher."""

from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest

from unbubble_sources.data import SearchQuery, Tweet, Usage
from unbubble_sources.search.x import XSearcher, _to_rfc3339


@pytest.fixture
def mock_response_data() -> dict[str, Any]:
    """Sample X API v2 response."""
    return {
        "data": [
            {
                "id": "111",
                "text": "Tweet one about tariffs",
                "author_id": "u1",
                "created_at": "2026-02-01T10:00:00.000Z",
                "public_metrics": {
                    "retweet_count": 5,
                    "like_count": 20,
                    "reply_count": 3,
                },
            },
            {
                "id": "222",
                "text": "Tweet two about tariffs",
                "author_id": "u2",
                "created_at": "2026-02-01T11:00:00.000Z",
                "public_metrics": {
                    "retweet_count": 10,
                    "like_count": 50,
                    "reply_count": 7,
                },
            },
        ],
        "includes": {
            "users": [
                {"id": "u1", "username": "alice", "name": "Alice A"},
                {"id": "u2", "username": "bob", "name": "Bob B"},
            ],
        },
    }


@pytest.fixture
def x_searcher() -> XSearcher:
    """Create a searcher with test bearer token."""
    return XSearcher(bearer_token="test-token")


def test_init_requires_bearer_token(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should raise if no bearer token provided."""
    monkeypatch.delenv("TWITTER_BEARER_TOKEN", raising=False)
    with pytest.raises(ValueError, match="bearer token required"):
        XSearcher()


def test_init_uses_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should use TWITTER_BEARER_TOKEN env var if no token passed."""
    monkeypatch.setenv("TWITTER_BEARER_TOKEN", "env-token")
    searcher = XSearcher()
    assert searcher._bearer_token == "env-token"


async def test_search_returns_tweets(
    x_searcher: XSearcher,
    mock_response_data: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should return list of Tweet objects."""
    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status = MagicMock()

    async def mock_get(*args: Any, **kwargs: Any) -> MagicMock:
        return mock_response

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    queries = [SearchQuery(text="tariffs", intent="trade policy")]
    sources, usage = await x_searcher.search(queries)

    assert len(sources) == 2
    assert all(isinstance(s, Tweet) for s in sources)
    tweet = sources[0]
    assert isinstance(tweet, Tweet)
    assert tweet.tweet_id == "111"
    assert tweet.author_handle == "alice"
    assert tweet.author_name == "Alice A"
    assert tweet.text == "Tweet one about tariffs"
    assert tweet.retweet_count == 5
    assert tweet.like_count == 20
    assert tweet.url == "https://x.com/alice/status/111"
    assert tweet.source == "x.com"
    assert tweet.query == queries[0]


async def test_search_returns_usage(
    x_searcher: XSearcher,
    mock_response_data: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should return usage with x_api_requests count."""
    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status = MagicMock()

    async def mock_get(*args: Any, **kwargs: Any) -> MagicMock:
        return mock_response

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    queries = [
        SearchQuery(text="query 1", intent="intent 1"),
        SearchQuery(text="query 2", intent="intent 2"),
    ]
    sources, usage = await x_searcher.search(queries)

    assert isinstance(usage, Usage)
    assert usage.x_api_requests == 2
    assert len(usage.api_calls) == 0  # No Claude API calls


async def test_search_deduplicates_by_url(
    x_searcher: XSearcher,
    mock_response_data: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should deduplicate tweets with same URL across queries."""
    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status = MagicMock()

    async def mock_get(*args: Any, **kwargs: Any) -> MagicMock:
        return mock_response

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    queries = [
        SearchQuery(text="query 1", intent="intent 1"),
        SearchQuery(text="query 2", intent="intent 2"),
    ]
    sources, usage = await x_searcher.search(queries)

    # Same response for both queries means same tweets, should dedup
    assert len(sources) == 2


async def test_search_passes_date_params(
    x_searcher: XSearcher,
    mock_response_data: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should pass start_time and end_time to API."""
    captured_params: dict[str, Any] = {}

    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status = MagicMock()

    async def mock_get(self: Any, url: str, **kwargs: Any) -> MagicMock:
        captured_params.update(kwargs.get("params", {}))
        return mock_response

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    queries = [SearchQuery(text="test", intent="test")]
    await x_searcher.search(
        queries,
        from_date="2026-01-01",
        to_date="2026-02-01",
        max_results_per_query=20,
    )

    assert captured_params["start_time"] == "2026-01-01T00:00:00Z"
    assert captured_params["end_time"] == "2026-02-01T00:00:00Z"
    assert captured_params["max_results"] == 20


async def test_search_handles_failed_queries(
    x_searcher: XSearcher,
    mock_response_data: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should skip failed queries and return results from successful ones."""
    call_count = 0

    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status = MagicMock()

    async def mock_get(self: Any, url: str, **kwargs: Any) -> MagicMock:
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
    sources, usage = await x_searcher.search(queries)

    assert len(sources) == 2
    # Only 1 request succeeded
    assert usage.x_api_requests == 1


async def test_search_clamps_max_results(
    x_searcher: XSearcher,
    mock_response_data: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Should clamp max_results between 10 and 100."""
    captured_params: dict[str, Any] = {}

    mock_response = MagicMock()
    mock_response.json.return_value = mock_response_data
    mock_response.raise_for_status = MagicMock()

    async def mock_get(self: Any, url: str, **kwargs: Any) -> MagicMock:
        captured_params.update(kwargs.get("params", {}))
        return mock_response

    monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

    queries = [SearchQuery(text="test", intent="test")]
    await x_searcher.search(queries, max_results_per_query=200)

    assert captured_params["max_results"] == 100  # Capped at 100


def test_to_rfc3339_date_only() -> None:
    """Should append T00:00:00Z to date-only strings."""
    assert _to_rfc3339("2026-01-01") == "2026-01-01T00:00:00Z"


def test_to_rfc3339_already_rfc3339() -> None:
    """Should return RFC 3339 strings unchanged."""
    assert _to_rfc3339("2026-01-01T10:00:00Z") == "2026-01-01T10:00:00Z"
