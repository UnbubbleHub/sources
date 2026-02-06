"""Unbubble: Open tools for research and applications against social polarization."""

from unbubble.aggregator.base import QueryAggregator
from unbubble.aggregator.pca import NoOpAggregator, PCAAggregator
from unbubble.config import UnbubbleConfig, create_from_config, load_config
from unbubble.pipeline.base import Pipeline
from unbubble.pipeline.claude_e2e import ClaudeE2EPipeline
from unbubble.pipeline.composable import ComposablePipeline
from unbubble.query.base import QueryGenerator
from unbubble.query.claude import DEFAULT_SYSTEM_PROMPT, ClaudeQueryGenerator
from unbubble.query.models import Article, NewsEvent, SearchQuery
from unbubble.search.base import ArticleSearcher
from unbubble.search.claude import ClaudeSearcher
from unbubble.search.gnews import GNewsSearcher

__all__ = [
    # Models
    "Article",
    "NewsEvent",
    "SearchQuery",
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
