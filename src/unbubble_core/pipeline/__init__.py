"""Pipeline module for end-to-end news discovery."""

from unbubble_core.pipeline.base import Pipeline
from unbubble_core.pipeline.claude_e2e import ClaudeE2EPipeline
from unbubble_core.pipeline.composable import ComposablePipeline

__all__ = [
    "ClaudeE2EPipeline",
    "ComposablePipeline",
    "Pipeline",
]
