"""Tests for the metrics protocol, runner, and NoOp placeholder."""

from collections.abc import Sequence
from unittest.mock import MagicMock

import pytest

from unbubble_sources.data import (
    AnnotatedSource,
    Article,
    PerspectiveAnnotation,
)
from unbubble_sources.metrics.base import Metric, MetricResult
from unbubble_sources.metrics.noop import NoOpMetric
from unbubble_sources.metrics.runner import MetricsRunner


@pytest.fixture
def sample_sources() -> list[AnnotatedSource]:
    return [
        AnnotatedSource(
            source=Article(
                title=f"Article {i}",
                url=f"https://example.com/{i}",
                source="example.com",
            ),
            annotation=PerspectiveAnnotation(),
        )
        for i in range(3)
    ]


def test_noop_metric_emits_source_count(sample_sources: list[AnnotatedSource]) -> None:
    metric = NoOpMetric()
    result = metric.compute(sample_sources)
    assert isinstance(result, MetricResult)
    assert result.name == "noop"
    assert result.value == pytest.approx(3.0)
    assert result.unit == "count"
    assert result.visualization is None


def test_runner_collects_results_in_order(sample_sources: list[AnnotatedSource]) -> None:
    class _StaticMetric:
        name = "static"
        visualization: str | None = None

        def compute(self, sources: Sequence[AnnotatedSource]) -> MetricResult:
            return MetricResult(name=self.name, value=1.0)

    runner = MetricsRunner([NoOpMetric(), _StaticMetric()])
    results = runner.run(sample_sources)
    assert [r.name for r in results] == ["noop", "static"]


def test_runner_isolates_per_metric_exceptions(
    sample_sources: list[AnnotatedSource],
) -> None:
    class _BrokenMetric:
        name = "broken"
        visualization: str | None = None

        def compute(self, sources: Sequence[AnnotatedSource]) -> MetricResult:
            raise RuntimeError("kaboom")

    runner = MetricsRunner([_BrokenMetric(), NoOpMetric()])
    results = runner.run(sample_sources)
    # Broken metric does NOT abort the runner; sibling still produces a
    # result.
    assert [r.name for r in results] == ["noop"]


def test_runner_pushes_results_through_logger(
    sample_sources: list[AnnotatedSource],
) -> None:
    mock_logger = MagicMock()
    runner = MetricsRunner([NoOpMetric()], run_logger=mock_logger)
    runner.run(sample_sources)
    mock_logger.log_metric.assert_called_once()
    args, _ = mock_logger.log_metric.call_args
    metric_name, result, duration = args
    assert metric_name == "noop"
    assert isinstance(result, MetricResult)
    assert duration >= 0.0


def test_runner_handles_logger_failure(sample_sources: list[AnnotatedSource]) -> None:
    """A broken logger must not abort metric computation."""
    broken_logger = MagicMock()
    broken_logger.log_metric.side_effect = RuntimeError("logger boom")
    runner = MetricsRunner([NoOpMetric()], run_logger=broken_logger)
    # Should still return the result even though the logger crashed.
    results = runner.run(sample_sources)
    assert [r.name for r in results] == ["noop"]


def test_metric_protocol_structurally_satisfied_by_noop() -> None:
    """NoOpMetric is structurally a Metric (Protocol check)."""
    m: Metric = NoOpMetric()
    assert m.name == "noop"
