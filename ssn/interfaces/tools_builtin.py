# ssn/interfaces/tools_builtin.py

from __future__ import annotations

from typing import Any, Dict

from ssn.interfaces.contracts import InterfaceRequest, InterfaceResponse, ErrorInfo
from ssn.interfaces.tool_bus import ToolBus, ToolSpec


def _safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {"value": x}


def register_builtin_tools(bus: ToolBus) -> None:
    """
    ToolBus builtin tools.

    IMPORTANT:
    - ToolBus is legacy/internal-only (InterfaceGateway action="tool").
    - Real system tools (net.*, research.*, memory.*, knowledge.*) live in ToolRegistry
      and are executed via action="run_tool" (handlers_tools.py) / orchestrator.tools.

    Therefore ToolBus builtins here are intentionally minimal, read-only,
    and do NOT overlap with ToolRegistry tool names to avoid confusion.
    """

    # ---------------------------------------------------------
    # toolbus.list (OWNER-only): list internal ToolBus tools
    # ---------------------------------------------------------
    def toolbus_list(req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
        try:
            return InterfaceResponse(
                ok=True,
                action=req.action,
                role=req.role,
                data={"tools": bus.list_tools()},
                error=None,
            )
        except Exception as e:
            return InterfaceResponse(
                ok=False,
                action=req.action,
                role=req.role,
                data={},
                error=ErrorInfo(code="TOOLBUS_LIST_ERROR", message=str(e), details={}),
            )

    bus.register(
        ToolSpec(
            name="toolbus.list",
            description="List ToolBus internal tools (legacy interface tools).",
            handler=toolbus_list,
            owner_only=True,
            read_only=True,
        )
    )

    # ---------------------------------------------------------
    # toolbus.ping (GUEST-allowed): health check
    # ---------------------------------------------------------
    def toolbus_ping(req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
        return InterfaceResponse(
            ok=True,
            action=req.action,
            role=req.role,
            data={"ok": True, "pong": True},
            error=None,
        )

    bus.register(
        ToolSpec(
            name="toolbus.ping",
            description="Simple ToolBus health check (guest-safe).",
            handler=toolbus_ping,
            owner_only=False,
            read_only=True,
        )
    )

    # ---------------------------------------------------------
    # safety.status (OWNER-only): safety monitor snapshot
    # ---------------------------------------------------------
    def safety_status(req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
        mon = deps.get("safety_monitor")
        if mon is None:
            return InterfaceResponse(
                ok=True,
                action=req.action,
                role=req.role,
                data={"available": False, "reason": "no_safety_monitor"},
                error=None,
            )
        snap = getattr(mon, "snapshot", None)
        out = snap() if callable(snap) else {"available": True}
        return InterfaceResponse(ok=True, action=req.action, role=req.role, data=_safe_dict(out), error=None)

    bus.register(
        ToolSpec(
            name="safety.status",
            description="Return safety monitor snapshot (ToolBus legacy).",
            handler=safety_status,
            owner_only=True,
            read_only=True,
        )
    )

    # ---------------------------------------------------------
    # policy.snapshot (OWNER-only): policy engine snapshot
    # ---------------------------------------------------------
    def policy_snapshot(req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
        pe = deps.get("policy_engine")
        if pe is None:
            return InterfaceResponse(
                ok=True,
                action=req.action,
                role=req.role,
                data={"available": False, "reason": "no_policy_engine"},
                error=None,
            )
        snap = getattr(pe, "snapshot", None)
        out = snap() if callable(snap) else {"available": True}
        return InterfaceResponse(ok=True, action=req.action, role=req.role, data=_safe_dict(out), error=None)

    bus.register(
        ToolSpec(
            name="policy.snapshot",
            description="Return policy engine snapshot (ToolBus legacy).",
            handler=policy_snapshot,
            owner_only=True,
            read_only=True,
        )
    )
