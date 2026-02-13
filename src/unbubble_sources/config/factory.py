"""Factory functions to create components from configuration."""

from pathlib import Path

from unbubble_sources.aggregator.pca import NoOpAggregator, PCAAggregator
from unbubble_sources.config.models import (
    ClaudeE2EPipelineConfig,
    ClaudeQueryGeneratorConfig,
    ClaudeSearcherConfig,
    ComposablePipelineConfig,
    ExaSearcherConfig,
    GNewsSearcherConfig,
    NoOpAggregatorConfig,
    NoOpQueryGeneratorConfig,
    PCAAggregatorConfig,
    QueryGeneratorConfig,
    SearcherConfig,
    UnbubbleConfig,
    XSearcherConfig,
)
from unbubble_sources.pipeline.base import Pipeline
from unbubble_sources.pipeline.claude_e2e import ClaudeE2EPipeline
from unbubble_sources.pipeline.composable import ComposablePipeline
from unbubble_sources.pricing import PriceCache
from unbubble_sources.query.base import QueryGenerator
from unbubble_sources.query.claude import ClaudeQueryGenerator
from unbubble_sources.query.noop import NoOpQueryGenerator
from unbubble_sources.run_logger import RunLogger
from unbubble_sources.search.base import SourceSearcher
from unbubble_sources.search.claude import ClaudeSearcher
from unbubble_sources.search.exa import ExaSearcher
from unbubble_sources.search.gnews import GNewsSearcher
from unbubble_sources.search.x import XSearcher


def create_generator(config: QueryGeneratorConfig) -> QueryGenerator:
    """Create a query generator from config.

    Uses explicit type matching rather than getattr.
    """
    if isinstance(config, ClaudeQueryGeneratorConfig):
        return ClaudeQueryGenerator(
            model=config.model,
            system_prompt=config.system_prompt,
        )
    if isinstance(config, NoOpQueryGeneratorConfig):
        return NoOpQueryGenerator()
    msg = f"Unknown generator config type: {type(config)}"
    raise ValueError(msg)


def create_searcher(
    config: SearcherConfig,
) -> SourceSearcher:
    """Create a source searcher from config."""
    if isinstance(config, ClaudeSearcherConfig):
        return ClaudeSearcher(
            model=config.model,
            max_searches_per_query=config.max_searches_per_query,
        )
    if isinstance(config, GNewsSearcherConfig):
        return GNewsSearcher(lang=config.lang)
    if isinstance(config, XSearcherConfig):
        return XSearcher(max_results_per_query=config.max_results_per_query)
    if isinstance(config, ExaSearcherConfig):
        return ExaSearcher(max_results_per_query=config.max_results_per_query)
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
    run_logger: RunLogger | None = None,
    price_cache: PriceCache | None = None,
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
            run_logger=run_logger,
            price_cache=price_cache,
        )
    if isinstance(config, ClaudeE2EPipelineConfig):
        return ClaudeE2EPipeline(
            model=config.model,
            target_articles=config.target_articles,
            run_logger=run_logger,
            price_cache=price_cache,
        )
    msg = f"Unknown pipeline config type: {type(config)}"
    raise ValueError(msg)


def create_from_config(
    config: UnbubbleConfig,
    *,
    log_override: bool | None = None,
    log_dir_override: str | None = None,
) -> tuple[Pipeline, RunLogger | None, PriceCache]:
    """Create a complete pipeline from root config.

    Args:
        config: Root configuration.
        log_override: Override the config's logging.enabled setting.
        log_dir_override: Override the config's logging.log_dir setting.

    Returns:
        Tuple of (pipeline, run_logger, price_cache).
        run_logger is None if logging is disabled.
    """
    log_enabled = log_override if log_override is not None else config.logging.enabled
    log_dir = Path(log_dir_override if log_dir_override is not None else config.logging.log_dir)

    run_logger: RunLogger | None = None
    if log_enabled:
        run_logger = RunLogger(log_dir=log_dir, enabled=True)

    price_cache = PriceCache()
    pipeline = create_pipeline(config.pipeline, run_logger=run_logger, price_cache=price_cache)
    return (pipeline, run_logger, price_cache)
