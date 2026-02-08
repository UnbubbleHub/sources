"""Factory functions to create components from configuration."""

from unbubble_core.aggregator.pca import NoOpAggregator, PCAAggregator
from unbubble_core.config.models import (
    ClaudeE2EPipelineConfig,
    ClaudeQueryGeneratorConfig,
    ClaudeSearcherConfig,
    ComposablePipelineConfig,
    GNewsSearcherConfig,
    NoOpAggregatorConfig,
    PCAAggregatorConfig,
    UnbubbleConfig,
)
from unbubble_core.pipeline.base import Pipeline
from unbubble_core.pipeline.claude_e2e import ClaudeE2EPipeline
from unbubble_core.pipeline.composable import ComposablePipeline
from unbubble_core.query.base import QueryGenerator
from unbubble_core.query.claude import ClaudeQueryGenerator
from unbubble_core.search.base import ArticleSearcher
from unbubble_core.search.claude import ClaudeSearcher
from unbubble_core.search.gnews import GNewsSearcher


def create_generator(config: ClaudeQueryGeneratorConfig) -> QueryGenerator:
    """Create a query generator from config.

    Uses explicit type matching rather than getattr.
    """
    return ClaudeQueryGenerator(
        model=config.model,
        system_prompt=config.system_prompt,
    )


def create_searcher(config: ClaudeSearcherConfig | GNewsSearcherConfig) -> ArticleSearcher:
    """Create an article searcher from config."""
    if isinstance(config, ClaudeSearcherConfig):
        return ClaudeSearcher(
            model=config.model,
            max_searches_per_query=config.max_searches_per_query,
        )
    if isinstance(config, GNewsSearcherConfig):
        return GNewsSearcher(lang=config.lang)
    # Type checker ensures this is exhaustive
    msg = f"Unknown searcher config type: {type(config)}"
    raise ValueError(msg)


def create_aggregator(
    config: PCAAggregatorConfig | NoOpAggregatorConfig,
) -> PCAAggregator | NoOpAggregator:
    """Create a query aggregator from config."""
    if isinstance(config, PCAAggregatorConfig):
        return PCAAggregator(
            n_components=config.n_components,
            sentence_transformer_model=config.sentence_transformer_model,
        )
    if isinstance(config, NoOpAggregatorConfig):
        return NoOpAggregator()
    msg = f"Unknown aggregator config type: {type(config)}"
    raise ValueError(msg)


def create_pipeline(
    config: ComposablePipelineConfig | ClaudeE2EPipelineConfig,
) -> Pipeline:
    """Create a pipeline from config."""
    if isinstance(config, ComposablePipelineConfig):
        generators = [create_generator(g) for g in config.generators]
        aggregator = create_aggregator(config.aggregator)
        searchers = [create_searcher(s) for s in config.searchers]

        return ComposablePipeline(
            generators=generators,
            aggregator=aggregator,
            searchers=searchers,
            num_queries_per_generator=config.num_queries_per_generator,
            max_results_per_searcher=config.max_results_per_searcher,
        )
    if isinstance(config, ClaudeE2EPipelineConfig):
        return ClaudeE2EPipeline(
            model=config.model,
            target_articles=config.target_articles,
        )
    msg = f"Unknown pipeline config type: {type(config)}"
    raise ValueError(msg)


def create_from_config(config: UnbubbleConfig) -> Pipeline:
    """Create a complete pipeline from root config."""
    return create_pipeline(config.pipeline)
