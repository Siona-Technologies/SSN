"""
Bounded structured observability for Phase 2 integration.
"""

from __future__ import annotations

import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class IntegrationMetrics:
    requests_by_mode: Dict[str, int] = field(default_factory=dict)
    events_by_type: Dict[str, int] = field(default_factory=dict)
    event_delivery_errors: int = 0
    queue_depth: int = 0
    workspace_count: int = 0
    workspace_evictions: int = 0
    attention_selections: int = 0
    router_selections: int = 0
    model_requests: int = 0
    model_shadow_observations: int = 0  # observations only — not duplicate calls
    provider_failures: int = 0
    provider_timeouts: int = 0
    fallback_count: int = 0
    neuromorphic_events: int = 0
    simulated_spike_count: int = 0
    tool_proposals: int = 0
    tool_results: int = 0
    tool_executions: int = 0
    memory_proposals: int = 0
    world_updates: int = 0
    perception_observations: int = 0
    request_latency_ms_last: float = 0.0
    duplicate_model_calls_prevented: int = 0

    def inc_mode(self, mode: str) -> None:
        m = str(mode or "legacy")
        self.requests_by_mode[m] = int(self.requests_by_mode.get(m, 0)) + 1

    def inc_event(self, event_type: str) -> None:
        # Bound cardinality: keep only first segment + second if present
        et = str(event_type or "unknown")
        parts = et.split(".")
        label = ".".join(parts[:2]) if len(parts) >= 2 else parts[0]
        if len(self.events_by_type) >= 64 and label not in self.events_by_type:
            label = "other"
        self.events_by_type[label] = int(self.events_by_type.get(label, 0)) + 1

    def snapshot(self) -> Dict[str, Any]:
        return {
            "ts": time.time(),
            "requests_by_mode": dict(self.requests_by_mode),
            "events_by_type": dict(self.events_by_type),
            "event_delivery_errors": self.event_delivery_errors,
            "queue_depth": self.queue_depth,
            "workspace_count": self.workspace_count,
            "workspace_evictions": self.workspace_evictions,
            "attention_selections": self.attention_selections,
            "router_selections": self.router_selections,
            "model_requests": self.model_requests,
            "model_shadow_observations": self.model_shadow_observations,
            "provider_failures": self.provider_failures,
            "provider_timeouts": self.provider_timeouts,
            "fallback_count": self.fallback_count,
            "neuromorphic_events": self.neuromorphic_events,
            "simulated_spike_count": self.simulated_spike_count,
            "tool_proposals": self.tool_proposals,
            "tool_results": self.tool_results,
            "tool_executions": self.tool_executions,
            "memory_proposals": self.memory_proposals,
            "world_updates": self.world_updates,
            "perception_observations": self.perception_observations,
            "request_latency_ms_last": self.request_latency_ms_last,
            "duplicate_model_calls_prevented": self.duplicate_model_calls_prevented,
            "note": "No secrets/master keys; bounded labels; diagnostic only.",
        }
