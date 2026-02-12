"""Tests for configuration loading and factory functions."""

from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from unbubble_sources.aggregator.pca import NoOpAggregator, PCAAggregator
from unbubble_sources.config import (
    ClaudeE2EPipelineConfig,
    ClaudeQueryGeneratorConfig,
    ClaudeSearcherConfig,
    ComposablePipelineConfig,
    GNewsSearcherConfig,
    NoOpAggregatorConfig,
    PCAAggregatorConfig,
    UnbubbleConfig,
    create_from_config,
    get_default_config_path,
    load_config,
)
from unbubble_sources.config.factory import (
    create_aggregator,
    create_generator,
    create_pipeline,
    create_searcher,
)
from unbubble_sources.pipeline.claude_e2e import ClaudeE2EPipeline
from unbubble_sources.pipeline.composable import ComposablePipeline
from unbubble_sources.query.claude import ClaudeQueryGenerator
from unbubble_sources.search.claude import ClaudeSearcher
from unbubble_sources.search.gnews import GNewsSearcher

# -- Config model tests --


def test_claude_generator_config_defaults() -> None:
    config = ClaudeQueryGeneratorConfig()
    assert config.type == "claude"
    assert config.model == "claude-haiku-4-5-20251001"
    assert config.system_prompt is None


def test_claude_searcher_config_defaults() -> None:
    config = ClaudeSearcherConfig()
    assert config.type == "claude"
    assert config.model == "claude-haiku-4-5-20251001"
    assert config.max_searches_per_query == 1


def test_gnews_searcher_config_defaults() -> None:
    config = GNewsSearcherConfig()
    assert config.type == "gnews"
    assert config.lang == "en"


def test_pca_aggregator_config_defaults() -> None:
    config = PCAAggregatorConfig()
    assert config.type == "pca"
    assert config.n_components == 5
    assert config.sentence_transformer_model == "all-MiniLM-L6-v2"


def test_noop_aggregator_config_defaults() -> None:
    config = NoOpAggregatorConfig()
    assert config.type == "noop"


def test_composable_pipeline_config_defaults() -> None:
    config = ComposablePipelineConfig()
    assert config.type == "composable"
    assert config.generators == []
    assert isinstance(config.aggregator, NoOpAggregatorConfig)
    assert config.searchers == []
    assert config.num_queries_per_generator == 5
    assert config.max_results_per_searcher == 10


def test_claude_e2e_pipeline_config_defaults() -> None:
    config = ClaudeE2EPipelineConfig()
    assert config.type == "claude_e2e"
    assert config.model == "claude-haiku-4-5-20251001"
    assert config.target_articles == 10


def test_unbubble_config_with_composable() -> None:
    config = UnbubbleConfig(pipeline=ComposablePipelineConfig())
    assert isinstance(config.pipeline, ComposablePipelineConfig)


def test_unbubble_config_with_e2e() -> None:
    config = UnbubbleConfig(pipeline=ClaudeE2EPipelineConfig())
    assert isinstance(config.pipeline, ClaudeE2EPipelineConfig)


# -- Config loader tests --


def test_load_config_composable() -> None:
    yaml_content = """
pipeline:
  type: composable
  generators:
    - type: claude
      model: claude-sonnet-4-20250514
  aggregator:
    type: pca
    n_components: 3
  searchers:
    - type: claude
      model: claude-haiku-4-5-20251001
  num_queries_per_generator: 10
  max_results_per_searcher: 5
"""
    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        config = load_config(Path(f.name))

    assert isinstance(config.pipeline, ComposablePipelineConfig)
    assert len(config.pipeline.generators) == 1
    assert config.pipeline.generators[0].model == "claude-sonnet-4-20250514"
    assert isinstance(config.pipeline.aggregator, PCAAggregatorConfig)
    assert config.pipeline.aggregator.n_components == 3
    assert config.pipeline.num_queries_per_generator == 10


def test_load_config_e2e() -> None:
    yaml_content = """
pipeline:
  type: claude_e2e
  model: claude-opus-4-20250514
  target_articles: 20
"""
    with NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()
        config = load_config(Path(f.name))

    assert isinstance(config.pipeline, ClaudeE2EPipelineConfig)
    assert config.pipeline.model == "claude-opus-4-20250514"
    assert config.pipeline.target_articles == 20


def test_get_default_config_path() -> None:
    path = get_default_config_path()
    assert path.name == "default.yaml"
    assert "configs" in str(path)


def test_load_default_config() -> None:
    path = get_default_config_path()
    if path.exists():
        config = load_config(path)
        assert isinstance(config, UnbubbleConfig)


# -- Factory function tests --


def test_create_generator_claude() -> None:
    config = ClaudeQueryGeneratorConfig(model="test-model")
    gen = create_generator(config)
    assert isinstance(gen, ClaudeQueryGenerator)


def test_create_searcher_claude() -> None:
    config = ClaudeSearcherConfig(model="test-model", max_searches_per_query=2)
    searcher = create_searcher(config)
    assert isinstance(searcher, ClaudeSearcher)


def test_create_searcher_gnews(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GNEWS_API_KEY", "test-key")
    config = GNewsSearcherConfig(lang="it")
    searcher = create_searcher(config)
    assert isinstance(searcher, GNewsSearcher)


def test_create_aggregator_pca() -> None:
    config = PCAAggregatorConfig(n_components=3)
    agg = create_aggregator(config)
    assert isinstance(agg, PCAAggregator)


def test_create_aggregator_noop() -> None:
    config = NoOpAggregatorConfig()
    agg = create_aggregator(config)
    assert isinstance(agg, NoOpAggregator)


def test_create_pipeline_composable() -> None:
    config = ComposablePipelineConfig(
        generators=[ClaudeQueryGeneratorConfig()],
        aggregator=NoOpAggregatorConfig(),
        searchers=[ClaudeSearcherConfig()],
    )
    pipeline = create_pipeline(config)
    assert isinstance(pipeline, ComposablePipeline)


def test_create_pipeline_e2e() -> None:
    config = ClaudeE2EPipelineConfig(target_articles=5)
    pipeline = create_pipeline(config)
    assert isinstance(pipeline, ClaudeE2EPipeline)


def test_create_from_config() -> None:
    config = UnbubbleConfig(pipeline=ClaudeE2EPipelineConfig())
    pipeline, run_logger, price_cache = create_from_config(config)
    assert isinstance(pipeline, ClaudeE2EPipeline)
    assert run_logger is None  # Logging disabled by default
    assert price_cache is not None


def test_create_from_config_with_logging() -> None:
    config = UnbubbleConfig(pipeline=ClaudeE2EPipelineConfig())
    pipeline, run_logger, price_cache = create_from_config(config, log_override=True)
    assert isinstance(pipeline, ClaudeE2EPipeline)
    assert run_logger is not None
    assert run_logger.enabled
    assert price_cache is not None
