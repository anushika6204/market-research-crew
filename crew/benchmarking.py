"""Execution benchmarking: per-task timing and task-routing history -> benchmarks.json."""
from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

log = logging.getLogger("benchmark")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class BenchmarkLogger:
    """Collects task durations and routing history for one crew run and appends it to a JSON file."""

    def __init__(self, path: str | Path, query: str, manager_model: str = "unknown"):
        self.path = Path(path)
        self.query = query
        self.manager_model = manager_model
        self.run_id = uuid.uuid4().hex[:8]
        self.tasks: list[dict[str, Any]] = []
        self.routing_history: list[dict[str, Any]] = []
        self._started_at = _now()
        self._t0 = self._last = time.perf_counter()

    # ---- lifecycle -----------------------------------------------------
    def start(self) -> None:
        self._started_at = _now()
        self._t0 = self._last = time.perf_counter()
        log.info("Benchmark run %s started for query: %s", self.run_id, self.query)

    def record_task(self, task_name: str, agent_role: str, output_text: str = "") -> dict[str, Any]:
        """Record a completed task. Duration = time since the previous task finished (tasks run sequentially)."""
        now = time.perf_counter()
        duration = round(now - self._last, 3)
        self._last = now
        step = len(self.tasks) + 1
        entry = {
            "order": step,
            "task": task_name,
            "agent": agent_role,
            "duration_seconds": duration,
            "completed_at": _now(),
            "output_chars": len(output_text or ""),
        }
        self.tasks.append(entry)
        self.routing_history.append(
            {"step": step, "task": task_name, "delegated_by": "Crew Manager", "assigned_to": agent_role}
        )
        log.info("[Routing] step %d: Manager -> '%s' | task '%s' finished in %.2fs", step, agent_role, task_name, duration)
        return entry

    def task_callback(self, task_name: str) -> Callable[[Any], None]:
        """Return a CrewAI Task callback that records the finished task and the agent that handled it."""

        def _callback(output: Any) -> None:
            agent_role = str(getattr(output, "agent", None) or "unknown")
            text = getattr(output, "raw", None) or str(output)
            self.record_task(task_name, agent_role, text)

        return _callback

    def finish(self, status: str = "completed", error: str | None = None) -> dict[str, Any]:
        """Finalise the run, append it to the JSON file and return the run record."""
        run = {
            "run_id": self.run_id,
            "query": self.query,
            "manager_model": self.manager_model,
            "status": status,
            "error": error,
            "started_at": self._started_at,
            "finished_at": _now(),
            "total_seconds": round(time.perf_counter() - self._t0, 3),
            "tasks": self.tasks,
            "routing_history": self.routing_history,
        }
        self._append(run)
        log.info("Benchmark run %s %s in %.2fs -> %s", self.run_id, status, run["total_seconds"], self.path)
        return run

    # ---- persistence ---------------------------------------------------
    def _append(self, run: dict[str, Any]) -> None:
        data: dict[str, Any] = {"runs": []}
        if self.path.exists():
            try:
                loaded = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(loaded, dict) and isinstance(loaded.get("runs"), list):
                    data = loaded
            except json.JSONDecodeError:
                log.warning("Existing %s was not valid JSON; starting a new file.", self.path)
        data["runs"].append(run)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
