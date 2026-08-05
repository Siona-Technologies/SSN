"""
Explicit trace context for Phase 2 integration.

Not authentication. One primary trace_id per request; child events reuse it.

Precedence for extract_or_create:
1. Explicit TraceContext argument
2. Current request context/meta fields
3. Request-local ContextVar (never shared deps)
4. Create a new trace at the interface boundary

Shared runtime deps must never store mutable per-request trace state.
"""

from __future__ import annotations

import time
import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from ssn.integration.runtime_modes import RuntimeMode, get_runtime_mode

# Request-local only — never process-wide mutable state on deps.
_request_trace: ContextVar[Optional["TraceContext"]] = ContextVar(
    "siona_request_trace", default=None
)


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
    def get_request_local(cls) -> Optional["TraceContext"]:
        return _request_trace.get()

    @classmethod
    def set_request_local(cls, trace: "TraceContext") -> Token:
        """Bind a TraceContext to the current async/task context only."""
        return _request_trace.set(trace)

    @classmethod
    def reset_request_local(cls, token: Token) -> None:
        _request_trace.reset(token)

    @classmethod
    def from_request(
        cls,
        *,
        context: Optional[Dict[str, Any]] = None,
        meta: Optional[Dict[str, Any]] = None,
        role: str = "GUEST",
        session_id: str = "",
        tenant_id: str = "default",
        source: str = "front_door",
        runtime_mode: Optional[str] = None,
    ) -> "TraceContext":
        ctx = dict(context or {})
        meta_d = dict(meta or {})
        # Nested meta inside context is also accepted.
        nested = ctx.get("meta") if isinstance(ctx.get("meta"), dict) else {}
        existing = (
            ctx.get("trace_id")
            or meta_d.get("trace_id")
            or nested.get("trace_id")
            or ctx.get("correlation_id")
            or meta_d.get("correlation_id")
            or nested.get("correlation_id")
            or ""
        )
        mode = runtime_mode or get_runtime_mode().value
        return cls(
            trace_id=str(existing) if existing else str(uuid.uuid4()),
            correlation_id=str(
                ctx.get("correlation_id")
                or meta_d.get("correlation_id")
                or nested.get("correlation_id")
                or existing
                or ""
            ),
            tenant_id=str(
                ctx.get("tenant_id")
                or meta_d.get("tenant_id")
                or nested.get("tenant_id")
                or tenant_id
                or "default"
            ),
            session_id=str(
                ctx.get("session_id")
                or meta_d.get("session_id")
                or nested.get("session_id")
                or session_id
                or ""
            ),
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
        meta: Optional[Dict[str, Any]] = None,
        deps: Optional[Dict[str, Any]] = None,
        role: str = "GUEST",
        source: str = "interface",
        runtime_mode: Optional[str] = None,
        trace: Optional["TraceContext"] = None,
    ) -> "TraceContext":
        """
        Resolve TraceContext for the current request.

        Never reads or writes deps["trace_context"]. deps may supply cognitive_mode only.
        """
        # 1. Explicit argument
        if isinstance(trace, TraceContext):
            return trace

        ctx = dict(context or {})
        meta_d = dict(meta or {})
        nested = ctx.get("meta") if isinstance(ctx.get("meta"), dict) else {}
        depsd = dict(deps or {})

        # 2. Current request context/meta fields win over any ambient ContextVar
        has_request_trace = bool(
            ctx.get("trace_id")
            or meta_d.get("trace_id")
            or nested.get("trace_id")
            or ctx.get("correlation_id")
            or meta_d.get("correlation_id")
            or nested.get("correlation_id")
        )
        if has_request_trace:
            mode = runtime_mode or depsd.get("cognitive_mode") or get_runtime_mode().value
            return cls.from_request(
                context=ctx,
                meta=meta_d,
                role=role,
                session_id=str(
                    ctx.get("session_id")
                    or meta_d.get("session_id")
                    or nested.get("session_id")
                    or ""
                ),
                tenant_id=str(
                    ctx.get("tenant_id")
                    or meta_d.get("tenant_id")
                    or nested.get("tenant_id")
                    or "default"
                ),
                source=source,
                runtime_mode=str(mode),
            )

        # 3. Request-local ContextVar (genuine ambient need only)
        local = _request_trace.get()
        if isinstance(local, TraceContext):
            if role and local.role != role:
                # Do not mutate shared ambient object — copy role for this resolution
                return cls(
                    trace_id=local.trace_id,
                    correlation_id=local.correlation_id,
                    tenant_id=local.tenant_id,
                    session_id=local.session_id,
                    role=str(role),
                    runtime_mode=local.runtime_mode,
                    started_at=local.started_at,
                    source=local.source,
                    metadata=dict(local.metadata),
                )
            return local

        # 4. Create once at the interface boundary
        mode = runtime_mode or depsd.get("cognitive_mode") or get_runtime_mode().value
        return cls.from_request(
            context=ctx,
            meta=meta_d,
            role=role,
            session_id=str(
                ctx.get("session_id")
                or meta_d.get("session_id")
                or nested.get("session_id")
                or ""
            ),
            tenant_id=str(
                ctx.get("tenant_id")
                or meta_d.get("tenant_id")
                or nested.get("tenant_id")
                or "default"
            ),
            source=source,
            runtime_mode=str(mode),
        )

    def bind_to_context(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Inject trace fields into a per-request context dict (never shared deps)."""
        ctx = dict(context or {})
        ctx["trace_id"] = self.trace_id
        ctx["correlation_id"] = self.correlation_id
        ctx.setdefault("tenant_id", self.tenant_id)
        ctx.setdefault("session_id", self.session_id)
        return ctx
