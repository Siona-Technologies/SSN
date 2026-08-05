"""Observation-only tool events — never executes tools."""

from __future__ import annotations

from typing import Any, Dict

from ssn.integration.event_bridge import EventBridge
from ssn.integration.redaction import redact
from ssn.integration.trace_context import TraceContext


class ToolBridge:
    def __init__(self, events: EventBridge, *, metrics: Any = None) -> None:
        self.events = events
        self.metrics = metrics
        self._execution_ids: set[str] = set()

    def on_proposed(self, *, tool_name: str, args: Dict[str, Any], trace: TraceContext) -> None:
        if self.metrics is not None:
            self.metrics.tool_proposals += 1
        self.events.emit_sync(
            "tool.proposed",
            source="integration.tools",
            payload={"tool": str(tool_name)[:128], "args": redact(args)},
            trace=trace,
        )

    def on_started(self, *, tool_name: str, execution_id: str, trace: TraceContext) -> None:
        self.events.emit_sync(
            "tool.started",
            source="integration.tools",
            payload={"tool": str(tool_name)[:128], "execution_id": execution_id},
            trace=trace,
        )

    def on_completed(
        self,
        *,
        tool_name: str,
        execution_id: str,
        ok: bool,
        result_summary: Dict[str, Any],
        trace: TraceContext,
        count_execution: bool = True,
    ) -> None:
        dup = execution_id in self._execution_ids
        if count_execution and not dup:
            self._execution_ids.add(execution_id)
            if self.metrics is not None:
                self.metrics.tool_executions += 1
                self.metrics.tool_results += 1
        elif dup and self.metrics is not None:
            self.metrics.tool_results += 1
        self.events.emit_sync(
            "tool.completed" if ok else "tool.failed",
            source="integration.tools",
            payload={
                "tool": str(tool_name)[:128],
                "execution_id": execution_id,
                "ok": bool(ok),
                "duplicate_observation": dup,
                "result": redact(result_summary),
            },
            trace=trace,
        )

    def register_execution(self, execution_id: str) -> bool:
        """Return True if this is the first registration (authoritative execution)."""
        if execution_id in self._execution_ids:
            return False
        self._execution_ids.add(execution_id)
        return True
