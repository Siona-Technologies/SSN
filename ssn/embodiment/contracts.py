"""
Embodiment and IoT contracts — body-independent, simulation-first.

SIONA owns the persistent mind; each body provides an EmbodimentAdapter.
No real actuators, doors, vehicles, or motors are connected in Phase 1.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol


class RiskClass(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ConnectivityStatus(str, Enum):
    ONLINE = "online"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNKNOWN = "unknown"
    SIMULATED = "simulated"


@dataclass(frozen=True)
class CapabilityDescriptor:
    name: str
    description: str = ""
    risk_class: RiskClass = RiskClass.LOW
    requires_confirmation: bool = True
    parameters_schema: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "risk_class": self.risk_class.value if isinstance(self.risk_class, RiskClass) else str(self.risk_class),
            "requires_confirmation": self.requires_confirmation,
            "parameters_schema": dict(self.parameters_schema),
            "metadata": dict(self.metadata),
        }


@dataclass
class DeviceDescriptor:
    device_id: str
    device_type: str
    location: str = ""
    owner_or_tenant: str = "default"
    capabilities: List[CapabilityDescriptor] = field(default_factory=list)
    current_state: Dict[str, Any] = field(default_factory=dict)
    risk_class: RiskClass = RiskClass.LOW
    connectivity: ConnectivityStatus = ConnectivityStatus.SIMULATED
    protocol: str = "mock"
    protocol_metadata: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "location": self.location,
            "owner_or_tenant": self.owner_or_tenant,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "current_state": dict(self.current_state),
            "risk_class": self.risk_class.value if isinstance(self.risk_class, RiskClass) else str(self.risk_class),
            "connectivity": self.connectivity.value if isinstance(self.connectivity, ConnectivityStatus) else str(self.connectivity),
            "protocol": self.protocol,
            "protocol_metadata": dict(self.protocol_metadata),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class SensorObservation:
    observation_id: str
    device_id: str
    sensor_name: str
    value: Any
    ts: float = field(default_factory=time.time)
    confidence: float = 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "device_id": self.device_id,
            "sensor_name": self.sensor_name,
            "value": self.value,
            "ts": self.ts,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ActionProposal:
    """Non-executing action proposal — requires authorization."""

    proposal_id: str
    capability: str
    target_device: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    confidence: float = 0.5
    risk_class: RiskClass = RiskClass.MEDIUM
    required_confirmation: bool = True
    trace_id: str = ""
    expiry_ts: float = 0.0
    expected_outcome: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, *, now: Optional[float] = None) -> bool:
        if self.expiry_ts <= 0:
            return False
        return float(now if now is not None else time.time()) > self.expiry_ts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "capability": self.capability,
            "target_device": self.target_device,
            "parameters": dict(self.parameters),
            "reason": self.reason,
            "confidence": self.confidence,
            "risk_class": self.risk_class.value if isinstance(self.risk_class, RiskClass) else str(self.risk_class),
            "required_confirmation": self.required_confirmation,
            "trace_id": self.trace_id,
            "expiry_ts": self.expiry_ts,
            "expected_outcome": self.expected_outcome,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ActionAuthorization:
    proposal_id: str
    authorized: bool
    authorized_by: str = ""
    reason: str = ""
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "authorized": self.authorized,
            "authorized_by": self.authorized_by,
            "reason": self.reason,
            "ts": self.ts,
        }


@dataclass(frozen=True)
class ActionResult:
    proposal_id: str
    ok: bool
    message: str = ""
    simulated: bool = True
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "ok": self.ok,
            "message": self.message,
            "simulated": self.simulated,
            "details": dict(self.details),
        }


@dataclass
class EmbodimentState:
    embodiment_id: str
    body_type: str  # computer | iot | vehicle | drone | robot | humanoid | mock
    connected: bool = True
    cognitive_attached: bool = True
    device_ids: List[str] = field(default_factory=list)
    body_local_state: Dict[str, Any] = field(default_factory=dict)
    """Body-specific only: joints, calibration, serials — never mind state."""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "embodiment_id": self.embodiment_id,
            "body_type": self.body_type,
            "connected": self.connected,
            "cognitive_attached": self.cognitive_attached,
            "device_ids": list(self.device_ids),
            "body_local_state": dict(self.body_local_state),
            "metadata": dict(self.metadata),
        }


class EmbodimentAdapter(Protocol):
    name: str

    def describe(self) -> EmbodimentState:
        ...

    def list_devices(self) -> List[DeviceDescriptor]:
        ...

    def observe(self) -> List[SensorObservation]:
        ...

    def propose_action(
        self,
        capability: str,
        target_device: str,
        parameters: Dict[str, Any],
        *,
        reason: str = "",
        trace_id: str = "",
    ) -> ActionProposal:
        ...

    def simulate_action(
        self,
        proposal: ActionProposal,
        authorization: Optional[ActionAuthorization] = None,
    ) -> ActionResult:
        ...


# Future protocol adapter boundaries (not implemented — no deps added):
FUTURE_PROTOCOL_ADAPTERS = (
    "mqtt",
    "matter",
    "ros2",
    "zenoh",
    "opcua",
    "http_websocket",
)
