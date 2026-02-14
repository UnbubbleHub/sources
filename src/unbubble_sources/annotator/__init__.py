"""Source annotation module."""

from unbubble_sources.annotator.base import SourceAnnotator
from unbubble_sources.annotator.claude import ClaudeAnnotator

__all__ = [
    "ClaudeAnnotator",
    "SourceAnnotator",
]
