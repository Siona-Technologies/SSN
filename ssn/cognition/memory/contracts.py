"""
Memory-system service boundaries (Phase 1 scaffolding).

Does not replace MemoryHub / JSON backends. Introduces typed records and
store protocols so PostgreSQL / vector / object storage can be added later
while preserving proposal → commit workflow.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, Sequence


class MemoryKind(str, Enum):
    WORKING = "working"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PREFERENCE = "preference"
    PROFILE = "profile"
    TRACE = "trace"
    PROCEDURAL = "procedural"  # placeholder
    SPATIAL = "spatial"  # placeholder
    SOCIAL = "social"  # placeholder
    SAFETY_INCIDENT = "safety_incident"  # placeholder
    SELF_MODEL = "self_model"  # placeholder


class RetentionClass(str, Enum):
    EPHEMERAL = "ephemeral"
    SESSION = "session"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    ARCHIVAL = "archival"


class ApprovalStatus(str, Enum):
    DRAFT = "draft"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


@dataclass
class MemoryRecord:
    """Typed memory record with provenance and retention metadata."""

    kind: MemoryKind
    content: Dict[str, Any]
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    confidence: float = 0.5
    freshness: float = 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    source: str = "unknown"
    tenant_id: str = "default"
    session_id: str = ""
    retention: RetentionClass = RetentionClass.SHORT_TERM
    approval: ApprovalStatus = ApprovalStatus.DRAFT
    version: int = 1
    supersedes: Optional[str] = None
    conflicts_with: List[str] = field(default_factory=list)
    provenance: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def touch(self) -> None:
        self.updated_at = time.time()
        self.version += 1

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "kind": self.kind.value if isinstance(self.kind, MemoryKind) else str(self.kind),
            "content": dict(self.content),
            "confidence": self.confidence,
            "freshness": self.freshness,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
            "retention": self.retention.value if isinstance(self.retention, RetentionClass) else str(self.retention),
            "approval": self.approval.value if isinstance(self.approval, ApprovalStatus) else str(self.approval),
            "version": self.version,
            "supersedes": self.supersedes,
            "conflicts_with": list(self.conflicts_with),
            "provenance": dict(self.provenance),
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class MemoryProposal:
    """Proposal destined for existing memory.propose → commit workflow."""

    proposal_id: str
    record: MemoryRecord
    reason: str = ""
    requires_owner_approval: bool = True
    trace_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "record": self.record.to_dict(),
            "reason": self.reason,
            "requires_owner_approval": self.requires_owner_approval,
            "trace_id": self.trace_id,
        }


class MemoryStore(Protocol):
    """Future-facing store protocol (JSON backend remains default)."""

    kind: MemoryKind

    def get(self, record_id: str) -> Optional[MemoryRecord]:
        ...

    def put(self, record: MemoryRecord) -> MemoryRecord:
        ...

    def list_recent(self, limit: int = 20) -> Sequence[MemoryRecord]:
        ...


class MemoryServiceBoundary:
    """
    Thin facade over existing MemoryHub.

    Read paths delegate to hub methods where available.
    Write paths produce MemoryProposal objects — they do NOT auto-commit.
    """

    def __init__(self, memory_hub: Any = None) -> None:
        self._hub = memory_hub
        self._working: Dict[str, MemoryRecord] = {}

    @property
    def hub(self) -> Any:
        return self._hub

    def propose(
        self,
        kind: MemoryKind,
        content: Dict[str, Any],
        *,
        reason: str = "",
        source: str = "cognition",
        confidence: float = 0.5,
        session_id: str = "",
        tenant_id: str = "default",
        trace_id: str = "",
        retention: RetentionClass = RetentionClass.SHORT_TERM,
    ) -> MemoryProposal:
        record = MemoryRecord(
            kind=kind,
            content=dict(content),
            confidence=confidence,
            source=source,
            session_id=session_id,
            tenant_id=tenant_id,
            retention=retention,
            approval=ApprovalStatus.PENDING,
            provenance={"trace_id": trace_id, "source": source},
        )
        if kind == MemoryKind.WORKING:
            self._working[record.record_id] = record
            record.approval = ApprovalStatus.APPROVED
            record.retention = RetentionClass.EPHEMERAL

        return MemoryProposal(
            proposal_id=str(uuid.uuid4()),
            record=record,
            reason=reason,
            requires_owner_approval=kind not in (MemoryKind.WORKING, MemoryKind.TRACE),
            trace_id=trace_id,
        )

    def recall_working(self) -> List[MemoryRecord]:
        return list(self._working.values())

    def recall_facts(self) -> List[Dict[str, Any]]:
        if self._hub is None:
            return []
        fn = getattr(self._hub, "recall_all_facts", None) or getattr(self._hub, "list_facts", None)
        if callable(fn):
            try:
                result = fn()
                if isinstance(result, list):
                    return result
                if isinstance(result, dict):
                    return [{"key": k, "value": v} for k, v in result.items()]
            except Exception:
                return []
        return []

    def recall_recent_events(self, n: int = 10) -> List[Dict[str, Any]]:
        if self._hub is None:
            return []
        fn = getattr(self._hub, "recall_recent_events", None)
        if callable(fn):
            try:
                result = fn(n) if n else fn()
                return list(result) if result else []
            except Exception:
                try:
                    return list(fn())
                except Exception:
                    return []
        return []

    def placeholder_kinds(self) -> List[str]:
        """Kinds scaffolded but not fully implemented."""
        return [
            MemoryKind.PROCEDURAL.value,
            MemoryKind.SPATIAL.value,
            MemoryKind.SOCIAL.value,
            MemoryKind.SAFETY_INCIDENT.value,
            MemoryKind.SELF_MODEL.value,
        ]
