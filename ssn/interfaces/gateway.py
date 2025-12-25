# ssn/interfaces/gateway.py

from __future__ import annotations

from typing import Any, Dict, Optional, Iterable

from ssn.interfaces.contracts import InterfaceRequest, InterfaceResponse, ErrorInfo
from ssn.interfaces.handlers import HANDLERS

from ssn.interfaces.handlers_world import handle_world
from ssn.interfaces.handlers_sense_tick import handle_sense_tick
from ssn.interfaces.handlers_tools import handle_run_tool


def _is_registry_like(obj: Any) -> bool:
    if obj is None:
        return False
    for attr in ("get", "run", "list"):
        if not callable(getattr(obj, attr, None)):
            return False
    return True


# -----------------------------
# Secret redaction (gateway-level)
# -----------------------------
_SECRET_KEYS_EXACT = {
    "master_key",
    "ssn_master_key",
    "api_key",
    "apikey",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "bearer",
    "secret",
    "password",
    "passwd",
    "private_key",
    "privatekey",
    "client_secret",
}
_SECRET_KEY_PREFIXES = (
    "auth",
    "bearer",
    "token",
    "secret",
    "password",
    "private",
    "access_",
    "refresh_",
    "api_key",
)


def _is_secret_key_name(name: str) -> bool:
    k = (name or "").strip().lower()
    if not k:
        return False
    if k in _SECRET_KEYS_EXACT:
        return True
    return any(k.startswith(p) for p in _SECRET_KEY_PREFIXES)


def _redact_str(s: str, secrets: Iterable[str]) -> str:
    out = s
    for sec in secrets:
        if isinstance(sec, str) and sec and sec in out:
            out = out.replace(sec, "[REDACTED]")
    return out


def _scrub_obj(x: Any, *, secrets: Iterable[str]) -> Any:
    """
    1) Remove secret-looking keys (master_key, token, etc.) from dicts.
    2) Redact secret values from strings if accidentally echoed.
    """
    if x is None:
        return None

    if isinstance(x, str):
        return _redact_str(x, secrets)

    if isinstance(x, dict):
        out: Dict[str, Any] = {}
        for k, v in x.items():
            if _is_secret_key_name(str(k)):
                continue
            out[str(k)] = _scrub_obj(v, secrets=secrets)
        return out

    if isinstance(x, list):
        return [_scrub_obj(v, secrets=secrets) for v in x]

    if isinstance(x, tuple):
        return tuple(_scrub_obj(v, secrets=secrets) for v in x)

    # For arbitrary objects, leave as-is (InterfaceResponse.data should be dict/list typically).
    return x


def _scrub_meta_for_policy(meta: Optional[dict]) -> dict:
    """
    Policy should never see master_key (or any secret values).
    Keep non-secret meta fields such as tool_name.
    """
    if not isinstance(meta, dict):
        return {}
    out: Dict[str, Any] = {}
    for k, v in meta.items():
        if _is_secret_key_name(str(k)):
            continue
        out[str(k)] = v
    return out


class InterfaceGateway:
    """
    Phase 4.0+ — Internal Interface Gateway

    Key rule:
      - "think" must be allowed to run for both OWNER and GUEST so SSN can respond
        (with internal restrictions if needed).
      - "world" and "sense_tick" are OWNER-verified inside their handlers.
      - "run_tool" is OWNER-verified inside its handler.
    """

    ALLOWED_ACTIONS = {
        "think",
        "explain_state",
        "summarize_memory",
        "suggest",
        "tool",        # legacy ToolBus dispatch
        "world",
        "sense_tick",
        "run_tool",
    }

    def __init__(
        self,
        *,
        orchestrator: Any = None,
        brain_router: Any = None,
        policy_engine: Any = None,
        safety_monitor: Any = None,
        memory_hub: Any = None,
        suggestion_engine: Any = None,
        tool_bus: Any = None,
        world_model: Any = None,
        world_context_provider: Any = None,
        perception_hub: Any = None,
        tool_registry: Any = None,
    ):
        self.deps: Dict[str, Any] = {
            "orchestrator": orchestrator,
            "brain_router": brain_router,
            "policy_engine": policy_engine,
            "safety_monitor": safety_monitor,
            "memory_hub": memory_hub,
            "suggestion_engine": suggestion_engine,
            "tool_bus": tool_bus,
            "world_model": world_model,
            "world_context_provider": world_context_provider,
            "perception_hub": perception_hub,
        }

        # Handy aliases for callers (FrontDoor, tests, etc.)
        self.deps.setdefault("gateway", self)
        self.deps.setdefault("interface_gateway", self)

        # Common aliases (helps FrontDoor/tools avoid split expectations)
        if policy_engine is not None:
            self.deps.setdefault("policy", policy_engine)
        if memory_hub is not None:
            self.deps.setdefault("memory", memory_hub)

        # ------------------------------------------------------
        # CRITICAL: ToolRegistry must be shared (no split-brain)
        # ------------------------------------------------------
        reg: Optional[Any] = None
        if _is_registry_like(tool_registry):
            reg = tool_registry
        else:
            orch = orchestrator
            if orch is not None:
                reg2 = getattr(orch, "tools", None) or getattr(orch, "tool_registry", None)
                if _is_registry_like(reg2):
                    reg = reg2

        if reg is not None:
            self.deps["tool_registry"] = reg
            self.deps.setdefault("tools", reg)

        # Ensure handlers are registered
        HANDLERS.setdefault("world", handle_world)
        HANDLERS.setdefault("sense_tick", handle_sense_tick)
        HANDLERS.setdefault("run_tool", handle_run_tool)

    def _policy_allows(self, req: InterfaceRequest) -> bool:
        """
        Gateway-level policy should NOT block "think" (chat), "world", "sense_tick",
        or "run_tool" at this layer. Those enforce restrictions internally.

        IMPORTANT SECURITY:
          - Never pass master_key into policy checks (scrub meta).
          - Never copy master_key from meta into context here.
        """
        if req.action in ("think", "explain_state", "world", "sense_tick", "run_tool"):
            return True

        pe = self.deps.get("policy_engine") or self.deps.get("policy")
        if pe is None:
            return True

        ctx = dict(req.context or {})
        meta_scrubbed = _scrub_meta_for_policy(req.meta if isinstance(req.meta, dict) else {})

        for m in ("is_allowed", "allow", "enforce", "check", "check_permission"):
            fn = getattr(pe, m, None)
            if callable(fn):
                try:
                    out = fn(role=req.role, action=req.action, context=ctx, meta=meta_scrubbed)
                    if isinstance(out, bool):
                        return out
                    if isinstance(out, dict):
                        return bool(out.get("allowed", False))
                    return True
                except Exception:
                    # Fail-open for non-critical actions to avoid bricking interface layer.
                    return True

        return True

    def _safety_allows(self, req: InterfaceRequest) -> bool:
        sm = self.deps.get("safety_monitor")
        if sm is None:
            return True

        for name in ("allow_internal_reflection", "allow_internal_analysis", "allow_internal_thought"):
            fn = getattr(sm, name, None)
            if callable(fn):
                try:
                    return bool(fn())
                except Exception:
                    return False
        return True

    def _scrub_response(self, req: InterfaceRequest, resp: InterfaceResponse) -> InterfaceResponse:
        """
        Final safety net: scrub InterfaceResponse so secrets can't leak even if a handler
        mistakenly echoes req.meta or other secret-bearing structures.
        """
        mk = None
        if isinstance(req.meta, dict):
            v = req.meta.get("master_key")
            if isinstance(v, str) and v:
                mk = v

        secrets = [mk] if isinstance(mk, str) and mk else []

        try:
            if resp is not None and getattr(resp, "data", None) is not None:
                resp.data = _scrub_obj(resp.data, secrets=secrets)  # type: ignore[attr-defined]
        except Exception:
            pass

        try:
            err = getattr(resp, "error", None)
            if err is not None:
                # scrub structured details if present
                try:
                    if getattr(err, "details", None) is not None:
                        err.details = _scrub_obj(err.details, secrets=secrets)  # type: ignore[attr-defined]
                except Exception:
                    pass
                # scrub message text if it accidentally contains the secret value
                try:
                    msg = getattr(err, "message", None)
                    if isinstance(msg, str) and secrets:
                        err.message = _redact_str(msg, secrets)  # type: ignore[attr-defined]
                except Exception:
                    pass
        except Exception:
            pass

        return resp

    def handle(self, req: InterfaceRequest) -> InterfaceResponse:
        if req.action not in self.ALLOWED_ACTIONS:
            return InterfaceResponse(
                ok=False,
                action=req.action,
                role=req.role,
                error=ErrorInfo(code="ACTION_NOT_ALLOWED", message=f"Unsupported action: {req.action}"),
            )

        if not self._policy_allows(req):
            return InterfaceResponse(
                ok=False,
                action=req.action,
                role=req.role,
                error=ErrorInfo(code="BLOCKED_BY_POLICY", message="Request blocked by policy."),
            )

        if not self._safety_allows(req):
            return InterfaceResponse(
                ok=False,
                action=req.action,
                role=req.role,
                error=ErrorInfo(code="BLOCKED_BY_SAFETY", message="Request blocked by safety monitor."),
            )

        # Legacy ToolBus dispatch (optional)
        if req.action == "tool":
            bus = self.deps.get("tool_bus")
            if bus is None:
                return InterfaceResponse(
                    ok=False,
                    action=req.action,
                    role=req.role,
                    error=ErrorInfo(code="NO_TOOL_BUS", message="ToolBus not wired."),
                )

            tool_name = req.meta.get("tool_name") if isinstance(req.meta, dict) else None
            if not isinstance(tool_name, str) or not tool_name.strip():
                return InterfaceResponse(
                    ok=False,
                    action=req.action,
                    role=req.role,
                    error=ErrorInfo(code="TOOL_NAME_MISSING", message="meta.tool_name is required."),
                )

            resp = bus.dispatch(tool_name.strip(), req, self.deps)
            return self._scrub_response(req, resp)

        handler = HANDLERS.get(req.action)
        if handler is None:
            return InterfaceResponse(
                ok=False,
                action=req.action,
                role=req.role,
                error=ErrorInfo(code="HANDLER_MISSING", message=f"No handler for action: {req.action}"),
            )

        resp = handler(req, self.deps)
        return self._scrub_response(req, resp)
