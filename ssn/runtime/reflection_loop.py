# ssn/runtime/reflection_loop.py

from __future__ import annotations

import time
from typing import Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    # Optional: only for type checkers; avoids runtime import failures
    from ssn.memory.memory_hub import MemoryHub
    from ssn.core.self_reflection import SelfReflection


class ReflectionLoop:
    """
    Phase 3.7 — Bounded Background Reflection Loop
    Internal-only, scheduler-invoked, single-pass (bounded).
    """

    MAX_STEPS = 3
    MAX_RUNTIME_SEC = 0.5

    def __init__(
        self,
        memory_hub: Any,         # MemoryHub-compatible object
        safety_monitor: Any,     # SafetyMonitor-compatible object
        self_reflection: Any,    # SelfReflection-compatible object
    ):
        self.memory_hub = memory_hub
        self.safety_monitor = safety_monitor
        self.self_reflection = self_reflection

    def _allow(self) -> bool:
        """
        Compatibility gate: supports different SafetyMonitor method names.
        """
        for name in (
            "allow_internal_reflection",
            "allow_internal_analysis",
            "allow_internal_thought",
        ):
            fn = getattr(self.safety_monitor, name, None)
            if callable(fn):
                return bool(fn())
        return True  # internal-only default

    def run_once(self) -> Dict[str, Any]:
        start_time = time.time()

        if not self._allow():
            return {"status": "aborted", "reason": "safety_denied"}

        get_traces = getattr(self.memory_hub, "get_recent_traces", None)
        get_episodic = getattr(self.memory_hub, "get_recent_episodic", None)

        trace = get_traces(limit=5) if callable(get_traces) else []
        episodic = get_episodic(limit=3) if callable(get_episodic) else []

        steps = 0
        reflection_notes = []

        while steps < self.MAX_STEPS:
            if time.time() - start_time > self.MAX_RUNTIME_SEC:
                break

            insight = self.self_reflection.inspect(
                trace_memory=trace,
                episodic_memory=episodic,
            )

            if insight:
                reflection_notes.append(insight)

            steps += 1

        summary = {
            "type": "reflection_summary",
            "steps": steps,
            "insights": reflection_notes,
            "timestamp": time.time(),
        }

        write_fn = getattr(self.memory_hub, "write_trace", None)
        if callable(write_fn):
            write_fn(source="reflection_loop", payload=summary, bounded=True)

        return {"status": "completed", "steps": steps}
