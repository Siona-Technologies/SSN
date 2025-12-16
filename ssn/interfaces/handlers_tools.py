# ssn/interfaces/handlers_tools.py

from __future__ import annotations

from typing import Any, Dict, Optional

from ssn.identity.owner_verification import verify_owner, is_samson_verified
from ssn.interfaces.contracts import InterfaceRequest, InterfaceResponse
from ssn.tools.registry import ToolRegistry
from ssn.tools.builtin_tools import register_builtin_tools


def _get_master_key(req: InterfaceRequest) -> Optional[str]:
    if isinstance(req.meta, dict):
        mk = req.meta.get("master_key")
        if isinstance(mk, str) and mk.strip():
            return mk.strip()
    if isinstance(req.context, dict):
        mk2 = req.context.get("master_key")
        if isinstance(mk2, str) and mk2.strip():
            return mk2.strip()
    return None


def _get_registry(deps: Dict[str, Any]) -> ToolRegistry:
    reg = deps.get("tool_registry")
    if isinstance(reg, ToolRegistry):
        return reg
    reg = ToolRegistry()
    register_builtin_tools(reg)
    deps["tool_registry"] = reg
    return reg


def handle_run_tool(req: InterfaceRequest, deps: Any) -> InterfaceResponse:
    """
    Phase 6.5A: Execute a registered tool (OWNER-only).

    Request contract (context):
      {
        "tool_name": "world.read",
        "args": {...}
      }
    """
    depsd = deps if isinstance(deps, dict) else {}
    mk = _get_master_key(req)

    scores = verify_owner(mk)
    if not is_samson_verified(scores):
        return InterfaceResponse(
            ok=True,
            action="run_tool",
            role=req.role,
            data={
                "identity_verified": False,
                "role": "GUEST",
                "allowed": False,
                "final_result": "BLOCKED_BY_POLICY",
                "scores": scores,
                "tool": None,
                "result": None,
            },
            error=None,
        )

    ctx = req.context if isinstance(req.context, dict) else {}
    tool_name = ctx.get("tool_name")
    args = ctx.get("args", {})
    if not isinstance(tool_name, str) or not tool_name.strip():
        return InterfaceResponse(
            ok=False,
            action="run_tool",
            role=req.role,
            data={"identity_verified": True, "allowed": True, "scores": scores},
            error={"code": "BAD_REQUEST", "message": "context.tool_name is required"},
        )

    if not isinstance(args, dict):
        args = {}

    # Ensure tools that wrap existing handlers can pass master_key down internally without leaking it elsewhere
    args = dict(args)
    if mk:
        args["master_key"] = mk

    reg = _get_registry(depsd)
    result = reg.run(name=tool_name.strip(), role="OWNER", deps=depsd, args=args)

    return InterfaceResponse(
        ok=bool(result.ok),
        action="run_tool",
        role=req.role,
        data={
            "identity_verified": True,
            "role": "OWNER",
            "allowed": True,
            "scores": scores,
            "tool": tool_name.strip(),
            "result": result.data if result.ok else None,
            "error": result.error if not result.ok else None,
        },
        error=None,
    )
