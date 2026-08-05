"""
Shared cognition contracts and proposal types.

Model / neuromorphic / embodiment outputs become structured proposals.
They never execute tools or actuators directly — existing policy and
control layers remain the validation boundary.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ProposalKind(str, Enum):
    REPLY = "reply"
    TOOL_CALL = "tool_call"
    MEMORY_WRITE = "memory_write"
    WORLD_UPDATE = "world_update"
    EMBODIMENT_ACTION = "embodiment_action"
    ATTENTION = "attention"
    REFLEX = "reflex"


class ProposalStatus(str, Enum):
    PROPOSED = "proposed"
    VALIDATED = "validated"
    REJECTED = "rejected"
    EXECUTED = "executed"
    EXPIRED = "expired"


@dataclass(frozen=True)
class CognitiveProposal:
    """
    Structured proposal produced by deliberative or neuromorphic paths.

    Must be validated by existing control layers before any side effect.
    """

    proposal_id: str
    kind: ProposalKind
    payload: Dict[str, Any] = field(default_factory=dict)
    reason: str = ""
    confidence: float = 0.5
    risk_class: str = "low"
    requires_confirmation: bool = True
    trace_id: str = ""
    correlation_id: str = ""
    source: str = "cognition"
    status: ProposalStatus = ProposalStatus.PROPOSED
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "kind": self.kind.value if isinstance(self.kind, ProposalKind) else str(self.kind),
            "payload": dict(self.payload),
            "reason": self.reason,
            "confidence": float(self.confidence),
            "risk_class": self.risk_class,
            "requires_confirmation": bool(self.requires_confirmation),
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "source": self.source,
            "status": self.status.value if isinstance(self.status, ProposalStatus) else str(self.status),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class CognitiveLoopResult:
    """Result of one cognitive-loop turn (request-response compatible)."""

    reply: str
    role: str
    proposals: List[CognitiveProposal] = field(default_factory=list)
    workspace_snapshot: Optional[Dict[str, Any]] = None
    events_published: int = 0
    engine: str = "cognitive-loop-v1"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reply": self.reply,
            "role": self.role,
            "proposals": [p.to_dict() for p in self.proposals],
            "workspace_snapshot": self.workspace_snapshot,
            "events_published": self.events_published,
            "engine": self.engine,
            "metadata": dict(self.metadata),
        }
