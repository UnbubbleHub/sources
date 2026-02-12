"""Pydantic configuration models for Unbubble components."""

from typing import Annotated, Literal

from pydantic import BaseModel, Field

# ============================================================
# Generator Configs
# ============================================================


class ClaudeQueryGeneratorConfig(BaseModel):
    """Configuration for ClaudeQueryGenerator."""

    type: Literal["claude"] = "claude"
    model: str = "claude-haiku-4-5-20251001"
    system_prompt: str | None = None

    model_config = {"frozen": True}


QueryGeneratorConfig = Annotated[
    ClaudeQueryGeneratorConfig,
    Field(discriminator="type"),
]


# ============================================================
# Searcher Configs
# ============================================================


class ClaudeSearcherConfig(BaseModel):
    """Configuration for ClaudeSearcher."""

    type: Literal["claude"] = "claude"
    model: str = "claude-haiku-4-5-20251001"
    max_searches_per_query: int = 1

    model_config = {"frozen": True}


class GNewsSearcherConfig(BaseModel):
    """Configuration for GNewsSearcher."""

    type: Literal["gnews"] = "gnews"
    lang: str = "en"

    model_config = {"frozen": True}


SearcherConfig = Annotated[
    ClaudeSearcherConfig | GNewsSearcherConfig,
    Field(discriminator="type"),
]


# ============================================================
# Aggregator Configs
# ============================================================


class PCAAggregatorConfig(BaseModel):
    """Configuration for PCA-based query aggregator."""

    type: Literal["pca"] = "pca"
    n_components: int = 5
    sentence_transformer_model: str = "all-MiniLM-L6-v2"

    model_config = {"frozen": True}


class NoOpAggregatorConfig(BaseModel):
    """Pass-through aggregator (no aggregation)."""

    type: Literal["noop"] = "noop"

    model_config = {"frozen": True}


AggregatorConfig = Annotated[
    PCAAggregatorConfig | NoOpAggregatorConfig,
    Field(discriminator="type"),
]


# ============================================================
# Pipeline Configs
# ============================================================


class ComposablePipelineConfig(BaseModel):
    """Configuration for composable pipeline."""

    type: Literal["composable"] = "composable"
    generators: list[ClaudeQueryGeneratorConfig] = Field(default_factory=list)
    aggregator: PCAAggregatorConfig | NoOpAggregatorConfig = Field(
        default_factory=NoOpAggregatorConfig
    )
    searchers: list[ClaudeSearcherConfig | GNewsSearcherConfig] = Field(default_factory=list)
    num_queries_per_generator: int = 5
    max_results_per_searcher: int = 10

    model_config = {"frozen": True}


class ClaudeE2EPipelineConfig(BaseModel):
    """Configuration for Claude E2E pipeline."""

    type: Literal["claude_e2e"] = "claude_e2e"
    model: str = "claude-haiku-4-5-20251001"
    target_articles: int = 10

    model_config = {"frozen": True}


PipelineConfig = Annotated[
    ComposablePipelineConfig | ClaudeE2EPipelineConfig,
    Field(discriminator="type"),
]


# ============================================================
# Logging Config
# ============================================================


class LoggingConfig(BaseModel):
    """Configuration for intermediate pipeline logging."""

    enabled: bool = False
    log_dir: str = "logs"

    model_config = {"frozen": True}


# ============================================================
# Root Config
# ============================================================


class UnbubbleConfig(BaseModel):
    """Root configuration for Unbubble."""

    pipeline: ComposablePipelineConfig | ClaudeE2EPipelineConfig
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    model_config = {"frozen": True}
