# ssn/interfaces/handlers_tools.py

from __future__ import annotations

import time
from typing import Any, Dict, Optional, Tuple

from ssn.identity.owner_verification import verify_owner, is_samson_verified
from ssn.interfaces.contracts import InterfaceRequest, InterfaceResponse
from ssn.tools.registry import ToolRegistry
from ssn.tools.builtin_tools import register_builtin_tools


# Tool run errors that mean "not permitted" (vs runtime failure)
_PERMISSION_DENIED_CODES = {
    "TOOL_NOT_FOUND",
    "TOOL_FORBIDDEN",
    "TOOL_STATE_CHANGE_FORBIDDEN",
    "RATE_LIMITED",
}


def _is_registry_like(obj: Any) -> bool:
    """
    Avoid strict isinstance-only checks to prevent accidental split-brain when
    registry is a proxy/subclass or injected object with same interface.
    """
    if obj is None:
        return False
    for attr in ("get", "run", "list"):
        if not callable(getattr(obj, attr, None)):
            return False
    return True


def _get_master_key(req: InterfaceRequest) -> Optional[str]:
    # Prefer meta first
    if isinstance(req.meta, dict):
        mk = req.meta.get("master_key")
        if isinstance(mk, str) and mk.strip():
            return mk.strip()

    # Fallback to context (legacy; CLI tries to avoid this)
    if isinstance(req.context, dict):
        mk2 = req.context.get("master_key")
        if isinstance(mk2, str) and mk2.strip():
            return mk2.strip()

    return None


def _get_registry(deps: Dict[str, Any]) -> Any:
    """
    CRITICAL:
    ToolRegistry must be a SINGLE shared instance (orchestrator.tools),
    otherwise tools appear "missing" or write to a different memory/stack.

    Order:
      1) deps["tool_registry"] (preferred)
      2) deps["orchestrator"].tools OR deps["orchestrator"].tool_registry (canonical)
      3) fallback: local ToolRegistry + builtin tools (last resort; tests/dev only)
    """
    reg = deps.get("tool_registry")
    if _is_registry_like(reg):
        return reg

    orch = deps.get("orchestrator")
    if orch is not None:
        reg2 = getattr(orch, "tools", None) or getattr(orch, "tool_registry", None)
        if _is_registry_like(reg2):
            deps["tool_registry"] = reg2
            return reg2

    # Last resort fallback (tests/dev only)
    reg3 = ToolRegistry()
    try:
        register_builtin_tools(reg3)
    except Exception:
        pass
    deps["tool_registry"] = reg3
    return reg3


def _get_memory_hub(deps: Dict[str, Any]) -> Any:
    mh = deps.get("memory_hub")
    if mh is not None:
        return mh
    orch = deps.get("orchestrator")
    if orch is not None:
        return getattr(orch, "memory_hub", None) or getattr(orch, "memory", None)
    return None


def _redact_args(args: Any) -> Dict[str, Any]:
    if not isinstance(args, dict):
        return {}

    out: Dict[str, Any] = {}
    for k, v in args.items():
        ks = str(k)
        if ks.lower() in {"master_key", "ssn_master_key"}:
            continue

        if isinstance(v, (str, int, float, bool)) or v is None:
            s = v
        elif isinstance(v, dict):
            sub: Dict[str, Any] = {}
            for i, (sk, sv) in enumerate(v.items()):
                if i >= 20:
                    break
                if str(sk).lower() in {"master_key", "ssn_master_key"}:
                    continue
                sub[str(sk)[:80]] = (sv if isinstance(sv, (int, float, bool)) else str(sv)[:240])
            s = sub
        elif isinstance(v, list):
            s = [str(x)[:200] for x in v[:20]]
        else:
            s = str(v)[:300]

        out[ks[:80]] = s

    return out


def _write_tool_trace(
    *,
    deps: Dict[str, Any],
    tool_name: str,
    args: Dict[str, Any],
    ok: bool,
    err: Any,
    approval_required: bool = False,
    approved: bool = False,
) -> None:
    mh = _get_memory_hub(deps)
    if mh is None:
        return

    add = (
        getattr(mh, "add_trace", None)
        or getattr(mh, "write_trace", None)
        or getattr(mh, "log_trace", None)
    )
    if not callable(add):
        return

    err_code = None
    err_msg = None
    if isinstance(err, dict):
        err_code = err.get("code")
        err_msg = err.get("message")

    payload = {
        "type": "tool_call",
        "ts": time.time(),
        "tool": tool_name,
        "ok": bool(ok),
        "approval_required": bool(approval_required),
        "approved": bool(approved),
        "args": _redact_args(args),
        "error": {
            "code": str(err_code)[:120] if err_code else None,
            "message": str(err_msg)[:240] if err_msg else None,
        },
        "source": "run_tool",
    }

    try:
        add(payload)
    except Exception:
        return


def _parse_tool_request(req: InterfaceRequest) -> Tuple[Optional[str], Dict[str, Any]]:
    ctx = req.context if isinstance(req.context, dict) else {}
    tool_name = ctx.get("tool_name")
    args = ctx.get("args", {})

    if not isinstance(tool_name, str) or not tool_name.strip():
        return None, {}

    if not isinstance(args, dict):
        args = {}

    args = dict(args)
    # never accept secrets through args
    args.pop("master_key", None)
    args.pop("ssn_master_key", None)

    return tool_name.strip(), args


def _build_approval_summary(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tool": tool_name,
        "action": "external_state_change",
        "args_preview": _redact_args(args),
        "note": "This action will affect an external system and requires OWNER approval.",
        "how_to_confirm": {"confirm": True},
    }


def _allowed_from_tool_result(result_ok: bool, result_error: Any) -> bool:
    """
    "allowed" means: permission was granted to attempt the tool.
    A tool can be allowed but still fail (network, parsing, etc.).
    """
    if result_ok:
        return True
    if isinstance(result_error, dict):
        code = result_error.get("code")
        if isinstance(code, str) and code in _PERMISSION_DENIED_CODES:
            return False
    return True


def handle_run_tool(req: InterfaceRequest, deps: Any) -> InterfaceResponse:
    depsd = deps if isinstance(deps, dict) else {}
    tool_name, args = _parse_tool_request(req)

    if tool_name is None:
        return InterfaceResponse(
            ok=False,
            action="run_tool",
            role=req.role,
            data={},
            error={"code": "BAD_REQUEST", "message": "context.tool_name is required"},
        )

    reg = _get_registry(depsd)

    # -----------------------------
    # GUEST path
    # -----------------------------
    if req.role == "GUEST":
        spec = reg.get(tool_name)
        if spec is None:
            return InterfaceResponse(
                ok=False,
                action="run_tool",
                role=req.role,
                data={
                    "identity_verified": False,
                    "role": "GUEST",
                    "allowed": False,
                    "tool": tool_name,
                    "result": None,
                    "error": {"code": "TOOL_NOT_FOUND", "message": tool_name},
                },
                error=None,
            )

        # Guest may only run: public + role allowed + not state-changing
        if (not bool(getattr(spec, "public", False))) or (not spec.is_role_allowed("GUEST")) or bool(getattr(spec, "state_changing", False)):
            return InterfaceResponse(
                ok=False,
                action="run_tool",
                role=req.role,
                data={
                    "identity_verified": False,
                    "role": "GUEST",
                    "allowed": False,
                    "final_result": "BLOCKED_BY_POLICY",
                    "tool": tool_name,
                    "result": None,
                },
                error=None,
            )

        result = reg.run(name=tool_name, role="GUEST", deps=depsd, args=args)

        return InterfaceResponse(
            ok=bool(result.ok),
            action="run_tool",
            role=req.role,
            data={
                "identity_verified": False,
                "role": "GUEST",
                "allowed": _allowed_from_tool_result(bool(result.ok), result.error),
                "tool": tool_name,
                "result": result.data if result.ok else None,
                "error": result.error if not result.ok else None,
            },
            error=None,
        )

    # -----------------------------
    # OWNER path (verified by master key)
    # -----------------------------
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
                "tool": tool_name,
                "result": None,
            },
            error=None,
        )

    spec = reg.get(tool_name)
    if spec is None:
        return InterfaceResponse(
            ok=False,
            action="run_tool",
            role=req.role,
            data={},
            error={"code": "TOOL_NOT_FOUND", "message": tool_name},
        )

    # -----------------------------
    # OWNER approval gate
    # -----------------------------
    if bool(getattr(spec, "requires_approval", False)):
        confirmed = bool(args.get("confirm") is True)
        if not confirmed:
            summary = _build_approval_summary(tool_name, args)

            _write_tool_trace(
                deps=depsd,
                tool_name=tool_name,
                args=args,
                ok=False,
                err={"code": "NEEDS_OWNER_APPROVAL", "message": "Explicit confirmation required"},
                approval_required=True,
                approved=False,
            )

            return InterfaceResponse(
                ok=False,
                action="run_tool",
                role=req.role,
                data={
                    "identity_verified": True,
                    "role": "OWNER",
                    "allowed": False,
                    "final_result": "NEEDS_OWNER_APPROVAL",
                    "scores": scores,
                    "tool": tool_name,
                    "approval": summary,
                },
                error=None,
            )

    # Inject master_key only after approval
    args2 = dict(args)
    if mk:
        args2["master_key"] = mk

    result = reg.run(name=tool_name, role="OWNER", deps=depsd, args=args2)

    _write_tool_trace(
        deps=depsd,
        tool_name=tool_name,
        args=args2,
        ok=bool(result.ok),
        err=(result.error if not result.ok else None),
        approval_required=bool(getattr(spec, "requires_approval", False)),
        approved=True,
    )

    return InterfaceResponse(
        ok=bool(result.ok),
        action="run_tool",
        role=req.role,
        data={
            "identity_verified": True,
            "role": "OWNER",
            "allowed": _allowed_from_tool_result(bool(result.ok), result.error),
            "scores": scores,
            "tool": tool_name,
            "result": result.data if result.ok else None,
            "error": result.error if not result.ok else None,
        },
        error=None,
    )
