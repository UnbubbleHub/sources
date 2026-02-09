"""Configuration module for Unbubble."""

from unbubble_core.config.factory import create_from_config
from unbubble_core.config.loader import get_default_config_path, load_config
from unbubble_core.config.models import (
    AggregatorConfig,
    ClaudeE2EPipelineConfig,
    ClaudeQueryGeneratorConfig,
    ClaudeSearcherConfig,
    ComposablePipelineConfig,
    GNewsSearcherConfig,
    NoOpAggregatorConfig,
    PCAAggregatorConfig,
    PipelineConfig,
    QueryGeneratorConfig,
    SearcherConfig,
    UnbubbleConfig,
)

__all__ = [
    "AggregatorConfig",
    "ClaudeE2EPipelineConfig",
    "ClaudeQueryGeneratorConfig",
    "ClaudeSearcherConfig",
    "ComposablePipelineConfig",
    "GNewsSearcherConfig",
    "NoOpAggregatorConfig",
    "PCAAggregatorConfig",
    "PipelineConfig",
    "QueryGeneratorConfig",
    "SearcherConfig",
    "UnbubbleConfig",
    "create_from_config",
    "get_default_config_path",
    "load_config",
]
