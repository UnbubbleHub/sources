"""Metric and MetricResult — describe pipeline output.

A *metric* in Unbubble Sources is a small, side-effect-free function
that consumes the final set of annotated sources and emits a
``MetricResult`` describing some property of that set: a scalar
(e.g. lean entropy, source count), a 2-D scatter (political compass,
embedding projection), a histogram, a heatmap, etc.

Metrics never alter the source set. They are designed so the meta-level
of a run — *which axes were considered, with what parameters, over how
many sources* — is observable from outside the pipeline, in line with
the project's "make the meta-level explicit" principle.

Visualisable metrics declare a ``visualization`` string identifying a
small, stable vocabulary of plot kinds (``scatter_2d``, ``bar``,
``histogram``, ``heatmap``, ``radar``, ``sankey``). The frontend ships
one renderer per kind; new frameworks (political compass, Nolan chart,
issue radar) almost always fit an existing kind.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from unbubble_sources.data import AnnotatedSource


@dataclass(frozen=True)
class MetricResult:
    """The output of a single ``Metric.compute`` call.

    Attributes:
        name: Identifier for the metric (e.g. ``"lean_entropy"``,
            ``"political_compass"``).
        value: Optional headline scalar. ``None`` for purely visual
            metrics whose information is in ``data``.
        unit: Optional unit (``"bits"``, ``"count"``, ``"probability"``,
            …) describing ``value``.
        visualization: Optional plot kind. One of a small fixed
            vocabulary the frontend understands. ``None`` for
            scalar-only metrics.
        data: Plot-ready payload. Shape is determined by
            ``visualization`` (e.g. for ``scatter_2d``: ``{"x_label":
            ..., "y_label": ..., "points": [{"x": ..., "y": ..., ...},
            ...]}``).
        metadata: Free-form dictionary recording the parameters used to
            compute the metric (weights, source count, model versions).
            Required per the meta-level-explicit principle.
    """

    name: str
    value: float | None = None
    unit: str | None = None
    visualization: str | None = None
    data: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class Metric(Protocol):
    """Interface for a single pipeline-output metric.

    Implementations are constructed from a Pydantic config (so they can
    be selected from YAML) and produce one ``MetricResult`` per
    ``compute`` call. Computation is synchronous: metrics should not
    do I/O.
    """

    name: str
    """Identifier used in config and logs (must match ``MetricResult.name``)."""

    visualization: str | None
    """Plot kind declared statically on the class; ``None`` for scalar-only."""

    def compute(self, sources: Sequence[AnnotatedSource]) -> MetricResult:
        """Compute the metric over the final ranked source set.

        Args:
            sources: The pipeline's final sources (annotated; may be
                empty).

        Returns:
            A ``MetricResult`` populated for this metric's
            ``visualization`` kind.
        """
        ...
