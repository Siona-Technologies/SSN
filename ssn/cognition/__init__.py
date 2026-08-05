"""
SIONA cognition foundation — event fabric, workspace, model/neuromorphic gateways.

This package is an additive layer. Existing Orchestrator / BrainRouter /
LanguageEngine / policy / owner-control paths remain authoritative.
"""

from __future__ import annotations

from ssn.cognition.events import CognitiveEvent, EventPriority, PrivacyClass
from ssn.cognition.event_bus import AsyncEventBus, EventBusMetrics
from ssn.cognition.workspace import GlobalCognitiveWorkspace, WorkspaceSnapshot
from ssn.cognition.attention import AttentionArbiter, AttentionDecision

__all__ = [
    "CognitiveEvent",
    "EventPriority",
    "PrivacyClass",
    "AsyncEventBus",
    "EventBusMetrics",
    "GlobalCognitiveWorkspace",
    "WorkspaceSnapshot",
    "AttentionArbiter",
    "AttentionDecision",
]
