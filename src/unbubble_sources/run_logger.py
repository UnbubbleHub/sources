"""Run logger for recording intermediate pipeline results to JSON files."""

import dataclasses
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from unbubble_sources.data import Usage


class StageRecord(BaseModel):
    """Record of a single pipeline stage execution."""

    stage: str
    component: str
    input: Any = None
    output: Any = None
    usage: dict[str, Any] | None = None
    cost_usd: float | None = None
    timestamp: str = ""
    duration_seconds: float = 0.0


class RunRecord(BaseModel):
    """Record of a complete pipeline run."""

    run_id: str
    pipeline_type: str
    event: dict[str, Any]
    started_at: str
    completed_at: str | None = None
    stages: list[StageRecord] = []
    final_source_count: int = 0
    total_usage: dict[str, Any] | None = None
    total_cost_usd: float | None = None


def _serialize(obj: Any) -> Any:
    """Serialize an object to JSON-compatible format.

    Handles dataclasses, Pydantic models, lists, dicts, and primitives.
    For Usage objects, includes computed property summaries.
    """
    if obj is None:
        return None
    if isinstance(obj, Usage):
        # Include computed properties alongside raw data
        return {
            "api_calls": [_serialize(c) for c in obj.api_calls],
            "gnews_requests": obj.gnews_requests,
            "x_api_requests": obj.x_api_requests,
            "exa_requests": obj.exa_requests,
            "input_tokens": obj.input_tokens,
            "output_tokens": obj.output_tokens,
            "cache_creation_input_tokens": obj.cache_creation_input_tokens,
            "cache_read_input_tokens": obj.cache_read_input_tokens,
            "web_searches": obj.web_searches,
            "estimated_cost": obj.estimated_cost,
        }
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if isinstance(obj, list):
        return [_serialize(item) for item in obj]
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, Path):
        return str(obj)
    return obj


class RunLogger:
    """Accumulates pipeline stage records and writes a JSON log file per run.

    When ``enabled=False``, all methods are no-ops — zero overhead.

    Args:
        log_dir: Directory to write JSON log files.
        enabled: If False, all methods become no-ops.
    """

    def __init__(self, log_dir: Path, *, enabled: bool = True) -> None:
        self._log_dir = log_dir
        self._enabled = enabled
        self._record: RunRecord | None = None
        self._last_log_path: Path | None = None

    @property
    def enabled(self) -> bool:
        """Whether logging is active."""
        return self._enabled

    @property
    def last_log_path(self) -> Path | None:
        """Path to the last written log file, or None."""
        return self._last_log_path

    def start_run(self, pipeline_type: str, event: Any) -> None:
        """Initialize a new run record.

        Args:
            pipeline_type: Type of pipeline (e.g. "composable", "claude_e2e").
            event: The pipeline input event.
        """
        if not self._enabled:
            return

        self._record = RunRecord(
            run_id=str(uuid.uuid4()),
            pipeline_type=pipeline_type,
            event=_serialize(event),
            started_at=datetime.now(tz=UTC).isoformat(),
        )

    def log_stage(
        self,
        stage: str,
        component: str,
        input_data: Any,
        output_data: Any,
        usage: Usage | None,
        duration_seconds: float,
    ) -> None:
        """Append a stage record to the current run.

        Args:
            stage: Stage name (e.g. "query_generation", "search").
            component: Component class name.
            input_data: Stage input (will be serialized).
            output_data: Stage output (will be serialized).
            usage: Usage object for this stage (None for non-API stages).
            duration_seconds: Wall-clock time for this stage.
        """
        if not self._enabled or self._record is None:
            return

        self._record.stages.append(
            StageRecord(
                stage=stage,
                component=component,
                input=_serialize(input_data),
                output=_serialize(output_data),
                usage=_serialize(usage) if usage is not None else None,
                cost_usd=usage.estimated_cost if usage is not None else None,
                timestamp=datetime.now(tz=UTC).isoformat(),
                duration_seconds=round(duration_seconds, 4),
            )
        )

    def finish_run(
        self,
        sources: list[Any],
        usage: Usage | None,
    ) -> Path | None:
        """Write the run record to a JSON file.

        Args:
            sources: Final list of sources produced by the pipeline.
            usage: Total accumulated usage.

        Returns:
            Path to the written JSON file, or None if logging is disabled.
        """
        if not self._enabled or self._record is None:
            return None

        self._record.completed_at = datetime.now(tz=UTC).isoformat()
        self._record.final_source_count = len(sources)
        self._record.total_usage = _serialize(usage) if usage is not None else None
        self._record.total_cost_usd = usage.estimated_cost if usage is not None else None

        # Ensure log directory exists
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Build filename: run_2026-02-12T14-30-00.json (colons → dashes)
        ts = self._record.started_at.replace(":", "-")
        # Remove microseconds and timezone info for cleaner filename
        ts = ts.split(".")[0].split("+")[0]
        filename = f"run_{ts}.json"
        filepath = self._log_dir / filename

        filepath.write_text(self._record.model_dump_json(indent=2))
        self._last_log_path = filepath
        return filepath
