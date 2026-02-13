"""Tests for RunLogger and serialization helpers."""

import json
from pathlib import Path

from unbubble_sources.data import (
    APICallUsage,
    Article,
    NewsEvent,
    SearchQuery,
    Tweet,
    Usage,
)
from unbubble_sources.run_logger import RunLogger, _serialize

# -- _serialize tests --


def test_serialize_none() -> None:
    assert _serialize(None) is None


def test_serialize_primitive() -> None:
    assert _serialize(42) == 42
    assert _serialize("hello") == "hello"
    assert _serialize(3.14) == 3.14
    assert _serialize(True) is True


def test_serialize_list() -> None:
    result = _serialize([1, "two", None])
    assert result == [1, "two", None]


def test_serialize_dict() -> None:
    result = _serialize({"a": 1, "b": "two"})
    assert result == {"a": 1, "b": "two"}


def test_serialize_dataclass() -> None:
    event = NewsEvent(description="Test event", date="2026-02-01")
    result = _serialize(event)
    assert isinstance(result, dict)
    assert result["description"] == "Test event"
    assert result["date"] == "2026-02-01"


def test_serialize_frozen_dataclass() -> None:
    call = APICallUsage(model="test-model", input_tokens=100, output_tokens=50)
    result = _serialize(call)
    assert isinstance(result, dict)
    assert result["model"] == "test-model"
    assert result["input_tokens"] == 100


def test_serialize_usage_includes_computed_properties() -> None:
    usage = Usage(
        api_calls=[
            APICallUsage(model="m1", input_tokens=100, output_tokens=50, web_searches=1),
            APICallUsage(model="m2", input_tokens=200, output_tokens=75, web_searches=2),
        ],
        gnews_requests=3,
        x_api_requests=5,
        exa_requests=2,
    )
    result = _serialize(usage)
    assert isinstance(result, dict)
    # Computed properties
    assert result["input_tokens"] == 300
    assert result["output_tokens"] == 125
    assert result["web_searches"] == 3
    assert result["gnews_requests"] == 3
    assert result["x_api_requests"] == 5
    assert result["exa_requests"] == 2
    assert result["estimated_cost"] == 0.0
    # Raw data
    assert len(result["api_calls"]) == 2


def test_serialize_tweet() -> None:
    tweet = Tweet(
        url="https://x.com/user/status/123",
        source="x.com",
        tweet_id="123",
        author_handle="user",
        text="Hello world",
    )
    result = _serialize(tweet)
    assert isinstance(result, dict)
    assert result["url"] == "https://x.com/user/status/123"
    assert result["source"] == "x.com"
    assert result["tweet_id"] == "123"
    assert result["author_handle"] == "user"
    assert result["text"] == "Hello world"


def test_serialize_nested_list_of_dataclasses() -> None:
    queries = [
        SearchQuery(text="q1", intent="i1"),
        SearchQuery(text="q2", intent="i2"),
    ]
    result = _serialize(queries)
    assert len(result) == 2
    assert result[0]["text"] == "q1"
    assert result[1]["intent"] == "i2"


def test_serialize_path() -> None:
    result = _serialize(Path("/some/path"))
    assert result == "/some/path"


# -- RunLogger disabled tests --


def test_run_logger_disabled_is_noop(tmp_path: Path) -> None:
    logger = RunLogger(log_dir=tmp_path, enabled=False)
    assert not logger.enabled

    logger.start_run("composable", NewsEvent(description="test"))
    logger.log_stage("test", "TestComponent", "input", "output", None, 1.0)
    result = logger.finish_run([], None)

    assert result is None
    assert logger.last_log_path is None
    # No files written
    assert list(tmp_path.iterdir()) == []


# -- RunLogger enabled tests --


def test_run_logger_start_and_finish(tmp_path: Path) -> None:
    logger = RunLogger(log_dir=tmp_path, enabled=True)
    assert logger.enabled

    event = NewsEvent(description="Test event")
    logger.start_run("composable", event)
    path = logger.finish_run([], None)

    assert path is not None
    assert path.exists()
    assert path.suffix == ".json"
    assert logger.last_log_path == path

    data = json.loads(path.read_text())
    assert data["pipeline_type"] == "composable"
    assert data["event"]["description"] == "Test event"
    assert data["final_source_count"] == 0
    assert data["completed_at"] is not None


def test_run_logger_log_stages(tmp_path: Path) -> None:
    logger = RunLogger(log_dir=tmp_path, enabled=True)

    event = NewsEvent(description="Test event")
    logger.start_run("composable", event)

    # Log a query generation stage
    queries = [SearchQuery(text="q1", intent="i1")]
    gen_usage = Usage(
        api_calls=[APICallUsage(model="claude-haiku-4-5", input_tokens=100, output_tokens=50)]
    )
    logger.log_stage(
        stage="query_generation",
        component="ClaudeQueryGenerator",
        input_data=event,
        output_data=queries,
        usage=gen_usage,
        duration_seconds=0.5,
    )

    # Log an aggregation stage (no usage)
    logger.log_stage(
        stage="aggregation",
        component="NoOpAggregator",
        input_data=queries,
        output_data=queries,
        usage=None,
        duration_seconds=0.01,
    )

    articles = [
        Article(title="A1", url="https://example.com/1", source="Example"),
    ]
    total_usage = Usage(
        api_calls=[APICallUsage(model="claude-haiku-4-5", input_tokens=100, output_tokens=50)]
    )
    path = logger.finish_run(articles, total_usage)

    assert path is not None
    data = json.loads(path.read_text())

    assert len(data["stages"]) == 2
    assert data["stages"][0]["stage"] == "query_generation"
    assert data["stages"][0]["component"] == "ClaudeQueryGenerator"
    assert data["stages"][0]["usage"] is not None
    assert data["stages"][0]["usage"]["input_tokens"] == 100
    assert data["stages"][0]["cost_usd"] == 0.0  # No price_cache stamped
    assert data["stages"][0]["duration_seconds"] == 0.5

    assert data["stages"][1]["stage"] == "aggregation"
    assert data["stages"][1]["usage"] is None
    assert data["stages"][1]["cost_usd"] is None
    assert data["stages"][1]["duration_seconds"] == 0.01

    assert data["final_source_count"] == 1
    assert data["total_usage"]["input_tokens"] == 100
    assert data["total_cost_usd"] == 0.0


def test_run_logger_creates_log_dir(tmp_path: Path) -> None:
    log_dir = tmp_path / "nested" / "logs"
    logger = RunLogger(log_dir=log_dir, enabled=True)

    logger.start_run("test", NewsEvent(description="test"))
    path = logger.finish_run([], None)

    assert path is not None
    assert log_dir.exists()


def test_run_logger_filename_format(tmp_path: Path) -> None:
    logger = RunLogger(log_dir=tmp_path, enabled=True)

    logger.start_run("test", NewsEvent(description="test"))
    path = logger.finish_run([], None)

    assert path is not None
    assert path.name.startswith("run_")
    assert path.name.endswith(".json")
    # Should not contain colons (filesystem-unsafe)
    assert ":" not in path.name


def test_run_logger_log_stage_without_start(tmp_path: Path) -> None:
    """log_stage before start_run should be a no-op."""
    logger = RunLogger(log_dir=tmp_path, enabled=True)
    # No start_run called — should not raise
    logger.log_stage("test", "TestComponent", "input", "output", None, 1.0)


def test_run_logger_finish_without_start(tmp_path: Path) -> None:
    """finish_run before start_run should return None."""
    logger = RunLogger(log_dir=tmp_path, enabled=True)
    result = logger.finish_run([], None)
    assert result is None


def test_run_logger_full_pipeline_integration(tmp_path: Path) -> None:
    """Simulate a full composable pipeline run with logging."""
    logger = RunLogger(log_dir=tmp_path, enabled=True)

    event = NewsEvent(description="US tariffs on China", date="2026-02-01")
    logger.start_run("composable", event)

    # Stage 1: Query generation
    queries = [
        SearchQuery(text="US tariffs China 2026", intent="general"),
        SearchQuery(text="China trade war impact", intent="economic"),
    ]
    gen_usage = Usage(
        api_calls=[
            APICallUsage(model="claude-haiku-4-5-20251001", input_tokens=150, output_tokens=80)
        ],
        estimated_cost=0.0006,
    )
    logger.log_stage("query_generation", "ClaudeQueryGenerator", event, queries, gen_usage, 1.2)

    # Stage 2: Aggregation
    logger.log_stage("aggregation", "NoOpAggregator", queries, queries, None, 0.001)

    # Stage 3: Search
    articles = [
        Article(title="Tariff article 1", url="https://a.com/1", source="Source A"),
        Article(title="Tariff article 2", url="https://b.com/2", source="Source B"),
    ]
    search_usage = Usage(
        api_calls=[
            APICallUsage(
                model="claude-haiku-4-5-20251001",
                input_tokens=200,
                output_tokens=100,
                web_searches=2,
            )
        ],
        estimated_cost=0.0207,
    )
    logger.log_stage("search", "ClaudeSearcher", queries, articles, search_usage, 3.5)

    # Stage 4: Deduplication
    logger.log_stage(
        "deduplication",
        "url_dedup",
        {"article_count": 2},
        {"article_count": 2},
        None,
        0.0001,
    )

    total_usage = gen_usage + search_usage
    path = logger.finish_run(articles, total_usage)

    assert path is not None
    data = json.loads(path.read_text())

    assert data["pipeline_type"] == "composable"
    assert data["event"]["description"] == "US tariffs on China"
    assert len(data["stages"]) == 4
    assert data["final_source_count"] == 2
    assert data["total_usage"]["input_tokens"] == 350
    assert data["total_usage"]["web_searches"] == 2
    assert data["total_usage"]["estimated_cost"] > 0

    # Verify per-stage cost
    assert data["stages"][0]["cost_usd"] == 0.0006
    assert data["stages"][1]["cost_usd"] is None  # aggregation has no usage
    assert data["stages"][2]["cost_usd"] == 0.0207
    assert data["stages"][3]["cost_usd"] is None  # dedup has no usage
    assert data["total_cost_usd"] > 0

    # Verify stage ordering
    stage_names = [s["stage"] for s in data["stages"]]
    assert stage_names == ["query_generation", "aggregation", "search", "deduplication"]
