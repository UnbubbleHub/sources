"""Unbubble Core: Open tools for research and applications against social polarization."""

from unbubble_core.aggregator.base import QueryAggregator
from unbubble_core.aggregator.pca import NoOpAggregator, PCAAggregator
from unbubble_core.config import UnbubbleConfig, create_from_config, load_config
from unbubble_core.data import Article, NewsEvent, SearchQuery
from unbubble_core.pipeline.base import Pipeline
from unbubble_core.pipeline.claude_e2e import ClaudeE2EPipeline
from unbubble_core.pipeline.composable import ComposablePipeline
from unbubble_core.query.base import QueryGenerator
from unbubble_core.query.claude import DEFAULT_SYSTEM_PROMPT, ClaudeQueryGenerator
from unbubble_core.search.base import ArticleSearcher
from unbubble_core.search.claude import ClaudeSearcher
from unbubble_core.search.gnews import GNewsSearcher
from unbubble_core.url import extract_domain

__all__ = [
    # Models
    "Article",
    "NewsEvent",
    "SearchQuery",
    # Functions
    "extract_domain",
    # Protocols
    "ArticleSearcher",
    "Pipeline",
    "QueryAggregator",
    "QueryGenerator",
    # Query Generators
    "ClaudeQueryGenerator",
    "DEFAULT_SYSTEM_PROMPT",
    # Searchers
    "ClaudeSearcher",
    "GNewsSearcher",
    # Aggregators
    "NoOpAggregator",
    "PCAAggregator",
    # Pipelines
    "ClaudeE2EPipeline",
    "ComposablePipeline",
    # Config
    "UnbubbleConfig",
    "create_from_config",
    "load_config",
]
