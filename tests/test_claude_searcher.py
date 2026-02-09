"""Tests for ClaudeSearcher."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from unbubble_sources.data import Article, SearchQuery
from unbubble_sources.search.claude import ClaudeSearcher
from unbubble_sources.url import extract_domain


@pytest.fixture
def mock_web_search_result() -> MagicMock:
    """Create a mock web search result."""
    result = MagicMock()
    result.type = "web_search_result"
    result.url = "https://example.com/article1"
    result.title = "Test Article"
    result.page_age = "February 1, 2026"
    return result


@pytest.fixture
def mock_response(mock_web_search_result: MagicMock) -> MagicMock:
    """Create a mock API response with web search results."""
    tool_result = MagicMock()
    tool_result.type = "web_search_tool_result"
    tool_result.content = [mock_web_search_result]

    response = MagicMock()
    response.content = [tool_result]
    return response


@pytest.fixture
def searcher(mock_response: MagicMock) -> ClaudeSearcher:
    """Create a searcher with mocked API client."""
    s = ClaudeSearcher(api_key="test-key")
    object.__setattr__(s._client.messages, "create", AsyncMock(return_value=mock_response))
    return s


async def test_search_returns_articles(searcher: ClaudeSearcher) -> None:
    queries = [SearchQuery(text="test query", intent="test intent")]
    articles = await searcher.search(queries)

    assert len(articles) == 1
    assert isinstance(articles[0], Article)
    assert articles[0].title == "Test Article"
    assert articles[0].url == "https://example.com/article1"


async def test_search_deduplicates_by_url(
    searcher: ClaudeSearcher, mock_response: MagicMock, mock_web_search_result: MagicMock
) -> None:
    """Should deduplicate articles with same URL across queries."""
    mock_response.content[0].content = [mock_web_search_result, mock_web_search_result]

    queries = [
        SearchQuery(text="query 1", intent="intent 1"),
        SearchQuery(text="query 2", intent="intent 2"),
    ]
    articles = await searcher.search(queries)

    assert len(articles) == 1


async def test_search_calls_api_with_web_search_tool(searcher: ClaudeSearcher) -> None:
    queries = [SearchQuery(text="test", intent="test")]
    await searcher.search(queries)

    mock_create: AsyncMock = searcher._client.messages.create  # type: ignore[assignment]
    call_kwargs = dict(mock_create.call_args.kwargs)
    assert "tools" in call_kwargs
    assert len(call_kwargs["tools"]) == 1
    assert call_kwargs["tools"][0]["type"] == "web_search_20250305"
    assert call_kwargs["tools"][0]["name"] == "web_search"


async def test_search_includes_date_in_prompt(searcher: ClaudeSearcher) -> None:
    queries = [SearchQuery(text="test", intent="test")]
    await searcher.search(queries, from_date="2026-01-01", to_date="2026-02-01")

    mock_create: AsyncMock = searcher._client.messages.create  # type: ignore[assignment]
    call_kwargs = dict(mock_create.call_args.kwargs)
    user_content = call_kwargs["messages"][0]["content"]
    assert "2026-01-01" in user_content
    assert "2026-02-01" in user_content


async def test_search_handles_failed_queries(
    searcher: ClaudeSearcher, mock_response: MagicMock
) -> None:
    """Should skip failed queries and continue."""
    call_count = 0

    async def mock_create(**kwargs: object) -> MagicMock:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("API error")
        return mock_response

    object.__setattr__(
        searcher._client.messages, "create", AsyncMock(side_effect=mock_create)
    )

    queries = [
        SearchQuery(text="failing query", intent="will fail"),
        SearchQuery(text="working query", intent="will work"),
    ]
    articles = await searcher.search(queries)

    assert len(articles) == 1


async def test_search_attaches_query_to_article(searcher: ClaudeSearcher) -> None:
    query = SearchQuery(text="specific query", intent="specific intent")
    articles = await searcher.search([query])

    assert len(articles) == 1
    assert articles[0].query == query


def test_extract_domain() -> None:
    assert extract_domain("https://www.example.com/path") == "example.com"
    assert extract_domain("https://news.example.com/article") == "news.example.com"
    assert extract_domain("invalid") == "Unknown"


def test_searcher_uses_env_var(monkeypatch: pytest.MonkeyPatch) -> None:
    """Should use CLAUDE_API_KEY env var if no key passed."""
    monkeypatch.setenv("CLAUDE_API_KEY", "env-key")
    searcher = ClaudeSearcher()
    assert searcher._client is not None
