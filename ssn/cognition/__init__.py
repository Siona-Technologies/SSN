"""
SIONA cognition foundation — event fabric, workspace, model/neuromorphic gateways.

This package is an additive layer. Existing Orchestrator / BrainRouter /
LanguageEngine / policy / owner-control paths remain authoritative.
"""

from __future__ import annotations

from ssn.cognition.events import CognitiveEvent, EventPriority, PrivacyClass
from ssn.cognition.event_bus import AsyncEventBus, EventBusMetrics, match_event_type
from ssn.cognition.workspace import (
    GlobalCognitiveWorkspace,
    WorkspaceRegistry,
    WorkspaceSnapshot,
    normalize_session_id,
    normalize_tenant_id,
    workspace_scope_key,
)
from ssn.cognition.attention import AttentionArbiter, AttentionDecision

__all__ = [
    "CognitiveEvent",
    "EventPriority",
    "PrivacyClass",
    "AsyncEventBus",
    "EventBusMetrics",
    "match_event_type",
    "GlobalCognitiveWorkspace",
    "WorkspaceRegistry",
    "WorkspaceSnapshot",
    "normalize_session_id",
    "normalize_tenant_id",
    "workspace_scope_key",
    "AttentionArbiter",
    "AttentionDecision",
]
