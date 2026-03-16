"""Tests for GrokSearcher."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from unbubble_sources.data import SearchQuery, Tweet
from unbubble_sources.search.grok import GrokSearcher, _extract_tweet_id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_query(text: str = "climate summit") -> SearchQuery:
    return SearchQuery(text=text, intent="test")


def _json_response(items: list[dict[str, object]]) -> dict[str, object]:
    """Build a minimal Grok Responses API reply with JSON in the text block."""
    import json
    return {
        "output": [
            {
                "type": "message",
                "content": [
                    {"type": "output_text", "text": json.dumps(items)},
                ],
            }
        ],
        "usage": {"input_tokens": 100, "output_tokens": 200},
    }


def _tweet_item(
    *,
    url: str = "https://x.com/user/status/1",
    handle: str = "user",
    name: str = "User Name",
    text: str = "Sample tweet",
    published_at: str | None = "2026-01-01T12:00:00Z",
    like_count: int = 5,
    retweet_count: int = 2,
    reply_count: int = 1,
) -> dict[str, object]:
    return {
        "url": url,
        "author_handle": handle,
        "author_name": name,
        "text": text,
        "published_at": published_at,
        "like_count": like_count,
        "retweet_count": retweet_count,
        "reply_count": reply_count,
    }


# ---------------------------------------------------------------------------
# GrokSearcher init
# ---------------------------------------------------------------------------


def test_init_requires_api_key() -> None:
    with patch.dict("os.environ", {}, clear=True):
        # Remove XAI_API_KEY if present
        import os
        os.environ.pop("XAI_API_KEY", None)
        with pytest.raises(ValueError, match="xAI API key"):
            GrokSearcher()


def test_init_uses_env_var() -> None:
    with patch.dict("os.environ", {"XAI_API_KEY": "xai-test-key"}):
        searcher = GrokSearcher()
        assert searcher._api_key == "xai-test-key"


def test_init_explicit_key() -> None:
    searcher = GrokSearcher(api_key="xai-explicit")
    assert searcher._api_key == "xai-explicit"


# ---------------------------------------------------------------------------
# _extract_tweet_id
# ---------------------------------------------------------------------------


def test_extract_tweet_id_standard() -> None:
    assert _extract_tweet_id("https://x.com/alice/status/123456789") == "123456789"


def test_extract_tweet_id_trailing_slash() -> None:
    assert _extract_tweet_id("https://x.com/alice/status/123/") == "123"


def test_extract_tweet_id_no_status() -> None:
    assert _extract_tweet_id("https://x.com/alice") == ""


# ---------------------------------------------------------------------------
# _try_parse_json_tweets
# ---------------------------------------------------------------------------


def test_parse_json_tweets_valid() -> None:
    searcher = GrokSearcher(api_key="xai-test")
    query = _make_query()
    items = [_tweet_item(url="https://x.com/alice/status/1", handle="alice")]
    tweets = searcher._try_parse_json_tweets(__import__("json").dumps(items), query)
    assert len(tweets) == 1
    assert isinstance(tweets[0], Tweet)
    assert tweets[0].author_handle == "alice"
    assert tweets[0].tweet_id == "1"


def test_parse_json_tweets_strips_code_fence() -> None:
    searcher = GrokSearcher(api_key="xai-test")
    query = _make_query()
    items = [_tweet_item()]
    raw = "```json\n" + __import__("json").dumps(items) + "\n```"
    tweets = searcher._try_parse_json_tweets(raw, query)
    assert len(tweets) == 1


def test_parse_json_tweets_invalid_json() -> None:
    searcher = GrokSearcher(api_key="xai-test")
    tweets = searcher._try_parse_json_tweets("not json", _make_query())
    assert tweets == []


def test_parse_json_tweets_skips_missing_url() -> None:
    searcher = GrokSearcher(api_key="xai-test")
    items = [{"author_handle": "bob", "text": "no url here"}]
    tweets = searcher._try_parse_json_tweets(__import__("json").dumps(items), _make_query())
    assert tweets == []


# ---------------------------------------------------------------------------
# search() — integration with mocked HTTP
# ---------------------------------------------------------------------------


@pytest.fixture
def searcher() -> GrokSearcher:
    return GrokSearcher(api_key="xai-test-key")


async def test_search_returns_tweets(searcher: GrokSearcher) -> None:
    items = [
        _tweet_item(url="https://x.com/alice/status/1", handle="alice"),
        _tweet_item(url="https://x.com/bob/status/2", handle="bob"),
    ]
    mock_response = MagicMock()
    mock_response.json.return_value = _json_response(items)
    mock_response.raise_for_status = MagicMock()

    with patch("unbubble_sources.search.grok.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        sources, usage = await searcher.search([_make_query()])

    assert len(sources) == 2
    assert all(isinstance(s, Tweet) for s in sources)
    assert usage.input_tokens == 100
    assert usage.output_tokens == 200


async def test_search_deduplicates_urls(searcher: GrokSearcher) -> None:
    """Same tweet returned by multiple queries should appear only once."""
    items = [_tweet_item(url="https://x.com/alice/status/1")]
    mock_response = MagicMock()
    mock_response.json.return_value = _json_response(items)
    mock_response.raise_for_status = MagicMock()

    with patch("unbubble_sources.search.grok.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        sources, _ = await searcher.search([_make_query("q1"), _make_query("q2")])

    assert len(sources) == 1


async def test_search_handles_http_error(searcher: GrokSearcher) -> None:
    """HTTP errors should be swallowed and an empty list returned."""
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = Exception("HTTP 500")

    with patch("unbubble_sources.search.grok.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        sources, usage = await searcher.search([_make_query()])

    assert sources == []
    assert usage.input_tokens == 0


async def test_search_respects_max_results(searcher: GrokSearcher) -> None:
    items = [_tweet_item(url=f"https://x.com/u/status/{i}") for i in range(20)]
    mock_response = MagicMock()
    mock_response.json.return_value = _json_response(items)
    mock_response.raise_for_status = MagicMock()

    with patch("unbubble_sources.search.grok.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value = mock_client

        sources, _ = await searcher.search([_make_query()], max_results_per_query=5)

    assert len(sources) <= 5
