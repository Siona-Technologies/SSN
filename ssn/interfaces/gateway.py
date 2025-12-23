# ssn/interfaces/gateway.py

from __future__ import annotations

from typing import Any, Dict, Optional

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

        # ------------------------------------------------------
        # CRITICAL: ToolRegistry must be shared (no split-brain)
        # ------------------------------------------------------
        # Precedence:
        #   1) explicitly provided tool_registry
        #   2) orchestrator.tools / orchestrator.tool_registry
        #   3) leave absent (handlers will last-resort fallback)
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

        # Ensure handlers are registered
        HANDLERS.setdefault("world", handle_world)
        HANDLERS.setdefault("sense_tick", handle_sense_tick)
        HANDLERS.setdefault("run_tool", handle_run_tool)

    def _policy_allows(self, req: InterfaceRequest) -> bool:
        """
        Gateway-level policy should NOT block "think" (chat), "world", "sense_tick",
        or "run_tool" at this layer. Those enforce restrictions internally.

        IMPORTANT SECURITY:
          - Do NOT copy master_key from meta into context here.
            Context must remain secret-free; handlers use meta["master_key"].
        """
        if req.action in ("think", "explain_state", "world", "sense_tick", "run_tool"):
            return True

        pe = self.deps.get("policy_engine")
        if pe is None:
            return True

        ctx = dict(req.context or {})
        meta = dict(req.meta or {})

        for m in ("is_allowed", "allow", "enforce", "check", "check_permission"):
            fn = getattr(pe, m, None)
            if callable(fn):
                try:
                    out = fn(role=req.role, action=req.action, context=ctx, meta=meta)
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

            return bus.dispatch(tool_name.strip(), req, self.deps)

        handler = HANDLERS.get(req.action)
        if handler is None:
            return InterfaceResponse(
                ok=False,
                action=req.action,
                role=req.role,
                error=ErrorInfo(code="HANDLER_MISSING", message=f"No handler for action: {req.action}"),
            )

        return handler(req, self.deps)
