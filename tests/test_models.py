"""Tests for data models."""

from unbubble_sources.data import Article, NewsEvent, SearchQuery, Source, Tweet


def test_news_event_minimal() -> None:
    event = NewsEvent(description="Test event")
    assert event.description == "Test event"
    assert event.date is None
    assert event.context is None


def test_news_event_full() -> None:
    event = NewsEvent(
        description="Test event",
        date="2026-02-01",
        context="Some context",
    )
    assert event.description == "Test event"
    assert event.date == "2026-02-01"
    assert event.context == "Some context"


def test_search_query() -> None:
    query = SearchQuery(text="test query", intent="test intent")
    assert query.text == "test query"
    assert query.intent == "test intent"


# -- Source hierarchy tests --


def test_source_base_fields() -> None:
    src = Source(url="https://example.com", source="example.com")
    assert src.url == "https://example.com"
    assert src.source == "example.com"
    assert src.published_at is None
    assert src.query is None


def test_article_inherits_source() -> None:
    article = Article(
        title="Test title",
        url="https://example.com/article",
        source="example.com",
    )
    assert isinstance(article, Source)
    assert article.title == "Test title"
    assert article.url == "https://example.com/article"
    assert article.description is None


def test_tweet_creation() -> None:
    tweet = Tweet(
        url="https://x.com/user/status/123",
        source="x.com",
        tweet_id="123",
        author_handle="user",
        author_name="User Name",
        text="Hello world",
        retweet_count=10,
        like_count=50,
        reply_count=5,
    )
    assert isinstance(tweet, Source)
    assert tweet.url == "https://x.com/user/status/123"
    assert tweet.source == "x.com"
    assert tweet.tweet_id == "123"
    assert tweet.author_handle == "user"
    assert tweet.text == "Hello world"
    assert tweet.retweet_count == 10
    assert tweet.like_count == 50
    assert tweet.reply_count == 5


def test_tweet_is_frozen() -> None:
    tweet = Tweet(url="https://x.com/u/status/1", source="x.com")
    try:
        tweet.text = "changed"  # type: ignore[misc]
        raise AssertionError("Should have raised FrozenInstanceError")
    except AttributeError:
        pass
