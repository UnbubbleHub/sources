"""Scoring primitives and protocols.

``Score`` is defined in :mod:`unbubble_sources.data` (because it is a
core dataclass carried on ``AnnotatedSource``); re-exported here for
ergonomic access alongside :class:`Scorer`.
"""

from unbubble_sources.data import Score
from unbubble_sources.scoring.base import Scorer

__all__ = ["Score", "Scorer"]
