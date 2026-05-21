"""Metric and MetricResult — describe pipeline output without changing it."""

from unbubble_sources.metrics.base import Metric, MetricResult
from unbubble_sources.metrics.noop import NoOpMetric
from unbubble_sources.metrics.runner import MetricsRunner

__all__ = ["Metric", "MetricResult", "MetricsRunner", "NoOpMetric"]
