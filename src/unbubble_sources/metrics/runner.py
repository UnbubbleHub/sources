"""MetricsRunner — execute a list of metrics over a source set.

The runner is a thin coordinator: it iterates the configured metrics,
catches per-metric failures (so one broken metric doesn't abort the
others), and returns the successful results. It also pushes each result
through any provided run/stream logger so the frontend can render
metrics progressively.
"""

import logging
import time
from collections.abc import Sequence
from typing import Protocol

from unbubble_sources.data import AnnotatedSource
from unbubble_sources.metrics.base import Metric, MetricResult

logger = logging.getLogger(__name__)


class _MetricLogger(Protocol):
    """Subset of the RunLogger / StreamLogger surface used by this runner."""

    def log_metric(
        self,
        metric_name: str,
        result: MetricResult,
        duration_seconds: float,
    ) -> None: ...


class MetricsRunner:
    """Execute a list of metrics over the final source set.

    Args:
        metrics: Metric implementations to run, in order.
        run_logger: Optional logger to push ``MetricResult`` events
            into. The logger must expose a ``log_metric`` method;
            both :class:`unbubble_sources.run_logger.RunLogger` and
            :class:`unbubble_sources.stream_logger.StreamLogger` do.
    """

    def __init__(
        self,
        metrics: list[Metric],
        *,
        run_logger: _MetricLogger | None = None,
    ) -> None:
        self._metrics = metrics
        self._run_logger = run_logger

    def run(self, sources: Sequence[AnnotatedSource]) -> list[MetricResult]:
        """Compute every metric and return the successful results.

        Per-metric exceptions are caught and logged; they do not abort
        sibling metrics. The list is returned in metric-config order
        (failed metrics are simply absent).

        Args:
            sources: Final pipeline sources to describe.

        Returns:
            One ``MetricResult`` per successful metric.
        """
        results: list[MetricResult] = []
        for metric in self._metrics:
            t0 = time.monotonic()
            try:
                result = metric.compute(sources)
            except Exception:
                logger.exception("Metric %r failed; skipping.", metric.name)
                continue
            duration = time.monotonic() - t0
            results.append(result)
            if self._run_logger is not None:
                try:
                    self._run_logger.log_metric(metric.name, result, duration)
                except Exception:
                    logger.exception(
                        "Failed to log metric %r; continuing.", metric.name
                    )
        return results
