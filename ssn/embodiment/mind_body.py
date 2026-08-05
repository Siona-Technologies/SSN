"""
Embodiment-independent identity principle (scaffold + documentation helpers).

SIONA owns the persistent mind; each physical or digital body provides an
embodiment adapter. This module does NOT alter owner verification, master-key
handling, or policy semantics — it only names transferable vs body-local state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


# Transferable cognitive state (mind) — eventually migratable across bodies.
TRANSFERABLE_MIND_KEYS = (
    "identity",
    "approved_long_term_memory",
    "preferences",
    "relationships",
    "knowledge",
    "policies",
    "learned_task_concepts",
    "high_level_skills",
    "self_model_history",
)

# Body-specific state — must remain with the embodiment adapter.
BODY_LOCAL_KEYS = (
    "joint_geometry",
    "motor_limits",
    "camera_calibration",
    "actuator_drivers",
    "balance_controllers",
    "force_constraints",
    "body_serial_numbers",
    "local_emergency_systems",
)


@dataclass(frozen=True)
class MindBodyBoundary:
    """Declarative split between transferable mind and body-local state."""

    mind_keys: List[str] = field(default_factory=lambda: list(TRANSFERABLE_MIND_KEYS))
    body_keys: List[str] = field(default_factory=lambda: list(BODY_LOCAL_KEYS))
    principle: str = (
        "SIONA owns the persistent mind; each physical or digital body "
        "provides an embodiment adapter."
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "principle": self.principle,
            "transferable_mind": list(self.mind_keys),
            "body_local": list(self.body_keys),
            "humanoid_motor_control": False,
            "phase": 1,
            "note": "Scaffold only — no motor control implemented.",
        }


def describe_mind_body_boundary() -> Dict[str, Any]:
    return MindBodyBoundary().to_dict()
