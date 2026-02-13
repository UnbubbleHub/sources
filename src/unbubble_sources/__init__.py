"""Unbubble Sources: Open tools for research and applications against social polarization."""

from unbubble_sources.aggregator.base import QueryAggregator
from unbubble_sources.aggregator.pca import NoOpAggregator, PCAAggregator
from unbubble_sources.config import UnbubbleConfig, create_from_config, load_config
from unbubble_sources.data import (
    APICallUsage,
    Article,
    NewsEvent,
    SearchQuery,
    Source,
    Tweet,
    Usage,
)
from unbubble_sources.pipeline.base import Pipeline
from unbubble_sources.pipeline.claude_e2e import ClaudeE2EPipeline
from unbubble_sources.pipeline.composable import ComposablePipeline
from unbubble_sources.pricing import (
    ModelPricing,
    PriceCache,
    estimate_api_call_cost,
    estimate_usage_cost,
    fetch_model_prices,
    get_model_pricing,
)
from unbubble_sources.query.base import QueryGenerator
from unbubble_sources.query.claude import DEFAULT_SYSTEM_PROMPT, ClaudeQueryGenerator
from unbubble_sources.query.noop import NoOpQueryGenerator
from unbubble_sources.run_logger import RunLogger
from unbubble_sources.search.base import ArticleSearcher, SourceSearcher
from unbubble_sources.search.claude import ClaudeSearcher
from unbubble_sources.search.exa import ExaSearcher
from unbubble_sources.search.gnews import GNewsSearcher
from unbubble_sources.search.x import XSearcher
from unbubble_sources.url import extract_domain

__all__ = [
    # Models
    "APICallUsage",
    "Article",
    "NewsEvent",
    "SearchQuery",
    "Source",
    "Tweet",
    "Usage",
    # Pricing
    "ModelPricing",
    "PriceCache",
    "estimate_api_call_cost",
    "estimate_usage_cost",
    "fetch_model_prices",
    "get_model_pricing",
    # Functions
    "extract_domain",
    # Protocols
    "ArticleSearcher",
    "Pipeline",
    "QueryAggregator",
    "QueryGenerator",
    "SourceSearcher",
    # Query Generators
    "ClaudeQueryGenerator",
    "DEFAULT_SYSTEM_PROMPT",
    "NoOpQueryGenerator",
    # Searchers
    "ClaudeSearcher",
    "ExaSearcher",
    "GNewsSearcher",
    "XSearcher",
    # Aggregators
    "NoOpAggregator",
    "PCAAggregator",
    # Pipelines
    "ClaudeE2EPipeline",
    "ComposablePipeline",
    # Logging
    "RunLogger",
    # Config
    "UnbubbleConfig",
    "create_from_config",
    "load_config",
]
