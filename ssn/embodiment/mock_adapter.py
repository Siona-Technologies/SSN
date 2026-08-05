"""
Mock / simulated embodiment adapter.

Never connects to real hardware. Action proposals are non-executing;
simulate_action records intent only.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from ssn.embodiment.contracts import (
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


class MockEmbodimentAdapter:
    """Simulated home/IoT-like embodiment for tests and demos."""

    name = "siona-mock-embodiment-v1"

    def __init__(
        self,
        *,
        embodiment_id: str = "mock-body-1",
        tenant_id: str = "default",
    ) -> None:
        self.embodiment_id = embodiment_id
        self.tenant_id = tenant_id
        self._devices = self._build_devices()
        self._observations: List[SensorObservation] = []
        self._simulated_actions: List[Dict[str, Any]] = []

    def _build_devices(self) -> List[DeviceDescriptor]:
        lamp = DeviceDescriptor(
            device_id="mock.lamp.living_room",
            device_type="light",
            location="living_room",
            owner_or_tenant=self.tenant_id,
            capabilities=[
                CapabilityDescriptor(
                    name="set_power",
                    description="Turn light on/off (simulated)",
                    risk_class=RiskClass.LOW,
                    requires_confirmation=True,
                    parameters_schema={"on": {"type": "boolean"}},
                ),
                CapabilityDescriptor(
                    name="set_brightness",
                    description="Set brightness 0-100 (simulated)",
                    risk_class=RiskClass.LOW,
                    requires_confirmation=True,
                    parameters_schema={"level": {"type": "integer", "min": 0, "max": 100}},
                ),
            ],
            current_state={"on": False, "brightness": 0},
            risk_class=RiskClass.LOW,
            connectivity=ConnectivityStatus.SIMULATED,
            protocol="mock",
            metadata={"simulated": True},
        )
        thermostat = DeviceDescriptor(
            device_id="mock.thermostat.main",
            device_type="thermostat",
            location="hallway",
            owner_or_tenant=self.tenant_id,
            capabilities=[
                CapabilityDescriptor(
                    name="set_temperature",
                    description="Set target temperature C (simulated)",
                    risk_class=RiskClass.MEDIUM,
                    requires_confirmation=True,
                    parameters_schema={"celsius": {"type": "number"}},
                ),
            ],
            current_state={"celsius": 21.0, "mode": "auto"},
            risk_class=RiskClass.MEDIUM,
            connectivity=ConnectivityStatus.SIMULATED,
            protocol="mock",
            metadata={"simulated": True},
        )
        return [lamp, thermostat]

    def describe(self) -> EmbodimentState:
        return EmbodimentState(
            embodiment_id=self.embodiment_id,
            body_type="mock",
            connected=True,
            cognitive_attached=True,
            device_ids=[d.device_id for d in self._devices],
            body_local_state={
                "note": "Body-local only; mind state lives in SIONA core",
                "simulated": True,
            },
            metadata={"adapter": self.name, "hardware": False},
        )

    def list_devices(self) -> List[DeviceDescriptor]:
        return list(self._devices)

    def observe(self) -> List[SensorObservation]:
        obs = [
            SensorObservation(
                observation_id=str(uuid.uuid4()),
                device_id="mock.thermostat.main",
                sensor_name="temperature_c",
                value=21.0,
                confidence=1.0,
                metadata={"simulated": True},
            )
        ]
        self._observations.extend(obs)
        return obs

    def propose_action(
        self,
        capability: str,
        target_device: str,
        parameters: Dict[str, Any],
        *,
        reason: str = "",
        trace_id: str = "",
    ) -> ActionProposal:
        device = next((d for d in self._devices if d.device_id == target_device), None)
        risk = device.risk_class if device else RiskClass.MEDIUM
        caps = {c.name: c for c in (device.capabilities if device else [])}
        cap = caps.get(capability)
        requires = True if cap is None else cap.requires_confirmation
        if cap is not None:
            risk = cap.risk_class

        return ActionProposal(
            proposal_id=str(uuid.uuid4()),
            capability=capability,
            target_device=target_device,
            parameters=dict(parameters),
            reason=reason or "mock_proposal",
            confidence=0.5,
            risk_class=risk,
            required_confirmation=requires,
            trace_id=trace_id or str(uuid.uuid4()),
            expiry_ts=time.time() + 60.0,
            expected_outcome=f"simulate {capability} on {target_device}",
            metadata={"simulated": True, "adapter": self.name},
        )

    def simulate_action(
        self,
        proposal: ActionProposal,
        authorization: Optional[ActionAuthorization] = None,
    ) -> ActionResult:
        """
        Record a simulated outcome. Does NOT touch real hardware.

        Without authorization (or authorized=False), returns rejected.
        Even when authorized, only mutates in-memory mock state.
        """
        if proposal.is_expired():
            return ActionResult(
                proposal_id=proposal.proposal_id,
                ok=False,
                message="proposal_expired",
                simulated=True,
            )
        if authorization is None or not authorization.authorized:
            return ActionResult(
                proposal_id=proposal.proposal_id,
                ok=False,
                message="not_authorized",
                simulated=True,
                details={"note": "Phase 1 never executes physical actions"},
            )

        # In-memory mock state update only
        for d in self._devices:
            if d.device_id != proposal.target_device:
                continue
            if proposal.capability == "set_power":
                d.current_state["on"] = bool(proposal.parameters.get("on", False))
            elif proposal.capability == "set_brightness":
                level = int(proposal.parameters.get("level", 0))
                d.current_state["brightness"] = max(0, min(100, level))
            elif proposal.capability == "set_temperature":
                d.current_state["celsius"] = float(proposal.parameters.get("celsius", 21.0))

        record = {
            "proposal": proposal.to_dict(),
            "authorization": authorization.to_dict(),
            "ts": time.time(),
        }
        self._simulated_actions.append(record)
        return ActionResult(
            proposal_id=proposal.proposal_id,
            ok=True,
            message="simulated_ok",
            simulated=True,
            details={"state_mutated": True, "hardware": False},
        )

    @property
    def simulated_action_log(self) -> List[Dict[str, Any]]:
        return list(self._simulated_actions)
