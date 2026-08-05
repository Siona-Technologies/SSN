"""
Structured cognition metrics (no secrets / no sensitive payloads).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class CognitionMetrics:
    """Process-local counters for the cognitive runtime foundation."""

    event_published: int = 0
    event_delivered: int = 0
    event_dropped: int = 0
    event_rejected: int = 0
    queue_depth: int = 0
    max_queue_depth: int = 0
    event_latency_ms_last: float = 0.0

    workspace_active_events: int = 0
    workspace_capacity: int = 0
    attention_selections: int = 0
    attention_rejections: int = 0

    model_requests: int = 0
    model_failures: int = 0
    model_fallbacks: int = 0
    model_tokens_in: int = 0
    model_tokens_out: int = 0

    neuromorphic_events: int = 0
    spike_count: int = 0

    tool_proposals: int = 0
    tool_executions_ok: int = 0
    tool_executions_fail: int = 0

    memory_proposals: int = 0
    world_updates: int = 0
    embodiment_proposals: int = 0

    extras: Dict[str, Any] = field(default_factory=dict)

    def merge_bus(self, bus_metrics: Dict[str, Any]) -> None:
        self.event_published = int(bus_metrics.get("published", self.event_published))
        self.event_delivered = int(bus_metrics.get("delivered", self.event_delivered))
        self.event_dropped = int(bus_metrics.get("dropped", self.event_dropped))
        self.event_rejected = int(bus_metrics.get("rejected", self.event_rejected))
        self.max_queue_depth = int(bus_metrics.get("max_queue_depth", self.max_queue_depth))
        self.event_latency_ms_last = float(bus_metrics.get("last_latency_ms", self.event_latency_ms_last))

    def snapshot(self) -> Dict[str, Any]:
        return {
            "event_published": self.event_published,
            "event_delivered": self.event_delivered,
            "event_dropped": self.event_dropped,
            "event_rejected": self.event_rejected,
            "queue_depth": self.queue_depth,
            "max_queue_depth": self.max_queue_depth,
            "event_latency_ms_last": self.event_latency_ms_last,
            "workspace_active_events": self.workspace_active_events,
            "workspace_capacity": self.workspace_capacity,
            "attention_selections": self.attention_selections,
            "attention_rejections": self.attention_rejections,
            "model_requests": self.model_requests,
            "model_failures": self.model_failures,
            "model_fallbacks": self.model_fallbacks,
            "model_tokens_in": self.model_tokens_in,
            "model_tokens_out": self.model_tokens_out,
            "neuromorphic_events": self.neuromorphic_events,
            "spike_count": self.spike_count,
            "tool_proposals": self.tool_proposals,
            "tool_executions_ok": self.tool_executions_ok,
            "tool_executions_fail": self.tool_executions_fail,
            "memory_proposals": self.memory_proposals,
            "world_updates": self.world_updates,
            "embodiment_proposals": self.embodiment_proposals,
            "extras": dict(self.extras),
        }
