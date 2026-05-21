"""Placeholder metric used to exercise pipeline plumbing.

Replaced in follow-up PRs (M3+) by concrete scalar and visual metrics
(``LeanEntropyMetric``, ``PoliticalCompassMetric``, …).
"""

from collections.abc import Sequence

from unbubble_sources.data import AnnotatedSource
from unbubble_sources.metrics.base import MetricResult


class NoOpMetric:
    """Trivial metric: reports the number of sources.

    Used today only to validate that the metrics stage runs end-to-end.
    A real metric replacement is expected in the M3/M4 PRs.
    """

    name: str = "noop"
    visualization: str | None = None

    def compute(self, sources: Sequence[AnnotatedSource]) -> MetricResult:
        return MetricResult(
            name=self.name,
            value=float(len(sources)),
            unit="count",
            visualization=None,
            data={},
            metadata={"description": "Placeholder metric — counts sources."},
        )
