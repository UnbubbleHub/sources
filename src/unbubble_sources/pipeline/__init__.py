"""Pipeline module for end-to-end news discovery."""

from unbubble_sources.pipeline.base import Pipeline
from unbubble_sources.pipeline.claude_e2e import ClaudeE2EPipeline
from unbubble_sources.pipeline.composable import ComposablePipeline

__all__ = [
    "ClaudeE2EPipeline",
    "ComposablePipeline",
    "Pipeline",
]
