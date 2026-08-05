"""
Explicit trace context for Phase 2 integration.

Not authentication. One primary trace_id per request; child events reuse it.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ssn.integration.runtime_modes import RuntimeMode, get_runtime_mode


@dataclass
class TraceContext:
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    correlation_id: str = ""
    tenant_id: str = "default"
    session_id: str = ""
    role: str = "GUEST"
    runtime_mode: str = RuntimeMode.LEGACY.value
    started_at: float = field(default_factory=time.time)
    source: str = "front_door"
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.correlation_id:
            self.correlation_id = self.trace_id
        if not self.tenant_id:
            self.tenant_id = "default"
        self.role = str(self.role or "GUEST")
        self.runtime_mode = str(self.runtime_mode or RuntimeMode.LEGACY.value)

    @classmethod
    def from_request(
        cls,
        *,
        context: Optional[Dict[str, Any]] = None,
        role: str = "GUEST",
        session_id: str = "",
        tenant_id: str = "default",
        source: str = "front_door",
        runtime_mode: Optional[str] = None,
    ) -> "TraceContext":
        ctx = dict(context or {})
        meta = ctx.get("meta") if isinstance(ctx.get("meta"), dict) else {}
        existing = (
            ctx.get("trace_id")
            or meta.get("trace_id")
            or ctx.get("correlation_id")
            or meta.get("correlation_id")
            or ""
        )
        mode = runtime_mode or get_runtime_mode().value
        return cls(
            trace_id=str(existing) if existing else str(uuid.uuid4()),
            correlation_id=str(ctx.get("correlation_id") or existing or ""),
            tenant_id=str(ctx.get("tenant_id") or meta.get("tenant_id") or tenant_id or "default"),
            session_id=str(ctx.get("session_id") or meta.get("session_id") or session_id or ""),
            role=str(role or "GUEST"),
            runtime_mode=str(mode),
            source=source,
            metadata={},
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "correlation_id": self.correlation_id,
            "tenant_id": self.tenant_id,
            "session_id": self.session_id,
            "role": self.role,
            "runtime_mode": self.runtime_mode,
            "started_at": self.started_at,
            "source": self.source,
            "metadata": dict(self.metadata),
        }

    def child_meta(self, **extra: Any) -> Dict[str, Any]:
        out = self.to_dict()
        out.update(extra)
        return out

    @classmethod
    def extract_or_create(
        cls,
        *,
        context: Optional[Dict[str, Any]] = None,
        deps: Optional[Dict[str, Any]] = None,
        role: str = "GUEST",
        source: str = "interface",
        runtime_mode: Optional[str] = None,
    ) -> "TraceContext":
        """
        Extract TraceContext from request context/deps, or create once at the boundary.

        Does not invent OWNER for observation — callers pass the already-resolved role.
        """
        ctx = dict(context or {})
        depsd = dict(deps or {})
        # Prefer an already-attached object on deps for the request lifetime.
        existing_obj = depsd.get("trace_context")
        if isinstance(existing_obj, TraceContext):
            if role and existing_obj.role != role:
                existing_obj.role = str(role)
            return existing_obj

        meta = ctx.get("meta") if isinstance(ctx.get("meta"), dict) else {}
        mode = runtime_mode or depsd.get("cognitive_mode") or get_runtime_mode().value
        tr = cls.from_request(
            context=ctx,
            role=role,
            session_id=str(ctx.get("session_id") or meta.get("session_id") or ""),
            tenant_id=str(ctx.get("tenant_id") or meta.get("tenant_id") or "default"),
            source=source,
            runtime_mode=str(mode),
        )
        return tr

    def bind_to_context(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Inject trace fields into a context dict for child handlers."""
        ctx = dict(context or {})
        ctx["trace_id"] = self.trace_id
        ctx["correlation_id"] = self.correlation_id
        ctx.setdefault("tenant_id", self.tenant_id)
        ctx.setdefault("session_id", self.session_id)
        return ctx

    def bind_to_deps(self, deps: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        depsd = dict(deps or {})
        depsd["trace_context"] = self
        return depsd
