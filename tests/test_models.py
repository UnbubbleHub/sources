"""Tests for data models."""

from unbubble.data import NewsEvent, SearchQuery


def test_news_event_minimal():
    event = NewsEvent(description="Test event")
    assert event.description == "Test event"
    assert event.date is None
    assert event.context is None


def test_news_event_full():
    event = NewsEvent(
        description="Test event",
        date="2026-02-01",
        context="Some context",
    )
    assert event.description == "Test event"
    assert event.date == "2026-02-01"
    assert event.context == "Some context"


def test_search_query():
    query = SearchQuery(text="test query", intent="test intent")
    assert query.text == "test query"
    assert query.intent == "test intent"
