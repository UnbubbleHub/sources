"""Tests for the Claude-based source annotator."""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from unbubble_sources.annotator.claude import ClaudeAnnotator, _parse_annotation
from unbubble_sources.data import (
    AnnotatedSource,
    Article,
    PolicyFrame,
    PoliticalLean,
    StakeholderType,
    Tweet,
    Usage,
)

# -- Fixtures --


@pytest.fixture
def sample_articles() -> list[Article]:
    return [
        Article(
            title="Climate bill passes Senate",
            url="https://example.com/1",
            source="example.com",
            description="Senate approves major climate legislation",
        ),
        Article(
            title="Economic impact of climate policy",
            url="https://biz.example.com/2",
            source="biz.example.com",
            description="Business analysis of new climate regulations",
        ),
    ]


@pytest.fixture
def sample_tweet() -> Tweet:
    return Tweet(
        url="https://x.com/user/status/123",
        source="x.com",
        tweet_id="123",
        author_handle="senator_x",
        author_name="Senator X",
        text="Proud to vote for the climate bill today!",
    )


@pytest.fixture
def mock_annotation_response() -> str:
    return json.dumps(
        [
            {
                "political_lean": "center_left",
                "policy_frames": ["economic", "policy_prescription"],
                "stakeholder_type": "journalist",
                "stance_summary": "Neutral reporting on Senate passage of climate bill",
                "topic": "climate policy",
                "geographic_focus": "United States",
                "relevance_score": 0.9,
            },
            {
                "political_lean": "center_right",
                "policy_frames": ["economic", "capacity_and_resources"],
                "stakeholder_type": "corporate",
                "stance_summary": "Analysis of business costs of new regulations",
                "topic": "climate policy",
                "geographic_focus": "United States",
                "relevance_score": 0.8,
            },
        ]
    )


def _make_mock_api_response(text: str) -> MagicMock:
    """Create a mock Anthropic API response."""
    text_block = MagicMock()
    text_block.text = text
    text_block.type = "text"

    usage = MagicMock()
    usage.input_tokens = 500
    usage.output_tokens = 200
    usage.cache_creation_input_tokens = 0
    usage.cache_read_input_tokens = 0
    usage.server_tool_use = None

    response = MagicMock()
    response.content = [text_block]
    response.usage = usage
    return response


# -- Unit tests for _parse_annotation --


def test_parse_annotation_valid() -> None:
    raw = {
        "political_lean": "left",
        "policy_frames": ["economic", "morality"],
        "stakeholder_type": "civil_society",
        "stance_summary": "Supports climate action",
        "topic": "environment",
        "geographic_focus": "EU",
        "relevance_score": 0.85,
    }
    annotation, relevance = _parse_annotation(raw)
    assert annotation.political_lean == PoliticalLean.LEFT
    assert PolicyFrame.ECONOMIC in annotation.policy_frames
    assert PolicyFrame.MORALITY in annotation.policy_frames
    assert annotation.stakeholder_type == StakeholderType.CIVIL_SOCIETY
    assert annotation.stance_summary == "Supports climate action"
    assert annotation.topic == "environment"
    assert annotation.geographic_focus == "EU"
    assert relevance == pytest.approx(0.85)


def test_parse_annotation_unknown_values() -> None:
    raw = {
        "political_lean": "invalid_lean",
        "policy_frames": ["economic", "invalid_frame"],
        "stakeholder_type": "invalid_type",
        "relevance_score": 1.5,  # Should be clamped
    }
    annotation, relevance = _parse_annotation(raw)
    assert annotation.political_lean == PoliticalLean.UNKNOWN
    assert annotation.policy_frames == (PolicyFrame.ECONOMIC,)
    assert annotation.stakeholder_type == StakeholderType.OTHER
    assert relevance == 1.0  # Clamped


def test_parse_annotation_empty() -> None:
    annotation, relevance = _parse_annotation({})
    assert annotation.political_lean == PoliticalLean.UNKNOWN
    assert annotation.policy_frames == ()
    assert annotation.stakeholder_type == StakeholderType.OTHER
    assert relevance == 0.0


# -- Integration tests for ClaudeAnnotator --


@pytest.fixture
def annotator(mock_annotation_response: str) -> ClaudeAnnotator:
    """Create annotator with mocked API client."""
    a = ClaudeAnnotator(api_key="test-key", batch_size=20)
    mock_response = _make_mock_api_response(mock_annotation_response)
    object.__setattr__(a._client.messages, "create", AsyncMock(return_value=mock_response))
    return a


async def test_annotate_returns_annotated_sources(
    annotator: ClaudeAnnotator, sample_articles: list[Article]
) -> None:
    results, usage = await annotator.annotate(sample_articles, "climate bill passes")
    assert len(results) == 2
    assert all(isinstance(r, AnnotatedSource) for r in results)


async def test_annotate_preserves_original_sources(
    annotator: ClaudeAnnotator, sample_articles: list[Article]
) -> None:
    results, _ = await annotator.annotate(sample_articles, "climate bill passes")
    assert results[0].source == sample_articles[0]
    assert results[1].source == sample_articles[1]


async def test_annotate_extracts_annotations(
    annotator: ClaudeAnnotator, sample_articles: list[Article]
) -> None:
    results, _ = await annotator.annotate(sample_articles, "climate bill passes")
    assert results[0].annotation.political_lean == PoliticalLean.CENTER_LEFT
    assert results[1].annotation.political_lean == PoliticalLean.CENTER_RIGHT
    assert results[0].relevance_score == pytest.approx(0.9)
    assert results[1].relevance_score == pytest.approx(0.8)


async def test_annotate_tracks_usage(
    annotator: ClaudeAnnotator, sample_articles: list[Article]
) -> None:
    _, usage = await annotator.annotate(sample_articles, "climate bill passes")
    assert isinstance(usage, Usage)
    assert len(usage.api_calls) == 1
    assert usage.input_tokens == 500
    assert usage.output_tokens == 200


async def test_annotate_empty_list(annotator: ClaudeAnnotator) -> None:
    results, usage = await annotator.annotate([], "no sources")
    assert results == []
    assert isinstance(usage, Usage)
    assert len(usage.api_calls) == 0


async def test_annotate_handles_malformed_json(
    sample_articles: list[Article],
) -> None:
    a = ClaudeAnnotator(api_key="test-key")
    mock_response = _make_mock_api_response("this is not valid json")
    object.__setattr__(a._client.messages, "create", AsyncMock(return_value=mock_response))
    results, _ = await a.annotate(sample_articles, "test event")
    # Should return default annotations
    assert len(results) == 2
    assert all(r.annotation.political_lean == PoliticalLean.UNKNOWN for r in results)
    assert all(r.relevance_score == 0.0 for r in results)


async def test_annotate_handles_markdown_fences(
    sample_articles: list[Article],
    mock_annotation_response: str,
) -> None:
    a = ClaudeAnnotator(api_key="test-key")
    fenced = f"```json\n{mock_annotation_response}\n```"
    mock_response = _make_mock_api_response(fenced)
    object.__setattr__(a._client.messages, "create", AsyncMock(return_value=mock_response))
    results, _ = await a.annotate(sample_articles, "test event")
    assert len(results) == 2
    assert results[0].annotation.political_lean == PoliticalLean.CENTER_LEFT


async def test_annotate_batching() -> None:
    """Test that sources are split into batches."""
    a = ClaudeAnnotator(api_key="test-key", batch_size=2)
    articles = [
        Article(title=f"Article {i}", url=f"https://example.com/{i}", source="example.com")
        for i in range(5)
    ]

    single_response = json.dumps(
        [
            {
                "political_lean": "center",
                "policy_frames": ["economic"],
                "stakeholder_type": "journalist",
                "stance_summary": "Neutral",
                "topic": "test",
                "geographic_focus": "US",
                "relevance_score": 0.5,
            },
        ]
        * 2
    )  # 2 per batch

    mock_create = AsyncMock(return_value=_make_mock_api_response(single_response))
    object.__setattr__(a._client.messages, "create", mock_create)

    results, usage = await a.annotate(articles, "test event")
    # 5 articles / batch_size=2 = 3 batches
    assert mock_create.call_count == 3
    assert len(results) == 5
