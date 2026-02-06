"""Pipeline module for end-to-end news discovery."""

from unbubble.pipeline.base import Pipeline
from unbubble.pipeline.claude_e2e import ClaudeE2EPipeline
from unbubble.pipeline.composable import ComposablePipeline

__all__ = [
    "ClaudeE2EPipeline",
    "ComposablePipeline",
    "Pipeline",
]
