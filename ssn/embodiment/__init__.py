"""
Embodiment fabric — body-independent interfaces for IoT / robotics / humanoids.

Principle: SIONA owns the persistent mind; each body is an adapter.
"""

from __future__ import annotations

from ssn.embodiment.contracts import (
    FUTURE_PROTOCOL_ADAPTERS,
    ActionAuthorization,
    ActionProposal,
    ActionResult,
    CapabilityDescriptor,
    ConnectivityStatus,
    DeviceDescriptor,
    EmbodimentState,
    RiskClass,
    SensorObservation,
)
from ssn.embodiment.mock_adapter import MockEmbodimentAdapter
from ssn.embodiment.mind_body import (
    BODY_LOCAL_KEYS,
    TRANSFERABLE_MIND_KEYS,
    MindBodyBoundary,
    describe_mind_body_boundary,
)

__all__ = [
    "FUTURE_PROTOCOL_ADAPTERS",
    "ActionAuthorization",
    "ActionProposal",
    "ActionResult",
    "CapabilityDescriptor",
    "ConnectivityStatus",
    "DeviceDescriptor",
    "EmbodimentState",
    "RiskClass",
    "SensorObservation",
    "MockEmbodimentAdapter",
    "BODY_LOCAL_KEYS",
    "TRANSFERABLE_MIND_KEYS",
    "MindBodyBoundary",
    "describe_mind_body_boundary",
]