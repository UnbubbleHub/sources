"""Stream logger that emits JSONL to stdout or a queue.

Drop-in replacement for RunLogger — same interface (start_run, log_stage,
finish_run) but instead of accumulating records and writing a file at the end,
it emits one JSON line per event.  When a ``queue.Queue`` is provided, lines
are pushed there (for the Vercel serverless function to stream over HTTP);
otherwise they go to stdout.
"""

from __future__ import annotations

import json
import queue
import sys
from datetime import UTC, datetime
from typing import Any

from unbubble_sources.data import Usage
from unbubble_sources.run_logger import _serialize

STAGE_STEPS: dict[str, int] = {
    "query_generation": 1,
    "aggregation": 2,
    "search": 3,
    "deduplication": 4,
    "annotation": 5,
    "ranking": 6,
    "e2e": 1,
}


class StreamLogger:
    """RunLogger-compatible logger that emits JSONL lines.

    Each call to ``log_stage`` produces one JSON line.  Lines are pushed to
    *output_queue* when provided, or printed to stdout otherwise.

    The pipeline checks ``if self._run_logger:`` before calling methods, so
    ``__bool__`` always returns True.
    """

    def __init__(self, output_queue: queue.Queue[dict[str, Any] | None] | None = None) -> None:
        self._queue = output_queue
        self._lines: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # RunLogger-compatible interface
    # ------------------------------------------------------------------

    def start_run(self, pipeline_type: str, event: Any) -> None:
        self._emit({
            "type": "start",
            "pipeline_type": pipeline_type,
            "event": _serialize(event),
            "timestamp": datetime.now(tz=UTC).isoformat(),
        })

    def log_stage(
        self,
        stage: str,
        component: str,
        input_data: Any,
        output_data: Any,
        usage: Usage | None,
        duration_seconds: float,
    ) -> None:
        self._emit({
            "type": "stage",
            "step": STAGE_STEPS.get(stage, 0),
            "stage": stage,
            "component": component,
            "output": _serialize(output_data),
            "usage": _serialize(usage) if usage is not None else None,
            "cost_usd": usage.estimated_cost if usage is not None else None,
            "duration_seconds": round(duration_seconds, 4),
            "timestamp": datetime.now(tz=UTC).isoformat(),
        })

    def finish_run(self, sources: list[Any], usage: Usage | None) -> None:
        self._emit({
            "type": "completed",
            "final_source_count": len(sources),
            "total_usage": _serialize(usage) if usage is not None else None,
            "total_cost_usd": usage.estimated_cost if usage is not None else None,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        })

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @property
    def enabled(self) -> bool:
        return True

    def get_lines(self) -> list[dict[str, Any]]:
        """Return all emitted lines (useful for testing)."""
        return list(self._lines)

    def _emit(self, data: dict[str, Any]) -> None:
        self._lines.append(data)
        if self._queue is not None:
            self._queue.put(data)
        else:
            print(json.dumps(data, default=str), file=sys.stdout, flush=True)
