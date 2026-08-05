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
    # NOTE: RATE_LIMITED is throttling, not permission denial.
}

# GUEST-ALLOWED INTROSPECTION (read-only)
_GUEST_ALLOWLIST = {"tools.list", "tools.public_list"}

# Keys that are almost always secrets
_SECRET_KEYS_EXACT = {
    "master_key", "ssn_master_key",
    "api_key", "apikey",
    "token", "access_token", "refresh_token",
    "authorization", "bearer",
    "secret", "password", "passwd",
    "private_key", "privatekey",
    "client_secret",
}

# Prefixes that are likely secrets
_SECRET_KEY_PREFIXES = (
    "auth",
    "bearer",
    "token",
    "secret",
    "password",
    "private",
    "api_key",
    "access_",
    "refresh_",
)


def _norm_role(role: Any) -> str:
    r = str(role or "GUEST").upper().strip()
    return r if r in ("OWNER", "GUEST") else "GUEST"


def _is_registry_like(obj: Any) -> bool:
    if obj is None:
        return False
    for attr in ("get", "run", "list"):
        if not callable(getattr(obj, attr, None)):
            return False
    return True


def _is_secret_key_name(name: str) -> bool:
    k = (name or "").strip().lower()
    if not k:
        return False
    if k in _SECRET_KEYS_EXACT:
        return True
    return any(k.startswith(p) for p in _SECRET_KEY_PREFIXES)


def _get_master_key(req: InterfaceRequest) -> Optional[str]:
    # Prefer meta first
    if isinstance(req.meta, dict):
        mk = req.meta.get("master_key")
        if isinstance(mk, str) and mk.strip():
            return mk.strip()

    # Prefer context.meta.master_key (frontdoor_cli uses this)
    if isinstance(req.context, dict):
        meta = req.context.get("meta")
        if isinstance(meta, dict):
            mk3 = meta.get("master_key")
            if isinstance(mk3, str) and mk3.strip():
                return mk3.strip()

        # Fallback to context (legacy)
        mk2 = req.context.get("master_key")
        if isinstance(mk2, str) and mk2.strip():
            return mk2.strip()

    return None


def _get_registry(deps: Dict[str, Any]) -> Any:
    reg = deps.get("tool_registry")
    if _is_registry_like(reg):
        return reg

    orch = deps.get("orchestrator")
    if orch is not None:
        reg2 = getattr(orch, "tools", None) or getattr(orch, "tool_registry", None)
        if _is_registry_like(reg2):
            deps["tool_registry"] = reg2
            return reg2

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
        ks = str(k)[:80]
        if _is_secret_key_name(ks):
            continue

        if isinstance(v, (str, int, float, bool)) or v is None:
            s = v
        elif isinstance(v, dict):
            sub: Dict[str, Any] = {}
            for i, (sk, sv) in enumerate(v.items()):
                if i >= 20:
                    break
                if _is_secret_key_name(str(sk)):
                    continue
                sub[str(sk)[:80]] = (sv if isinstance(sv, (int, float, bool)) else str(sv)[:240])
            s = sub
        elif isinstance(v, list):
            s = [str(x)[:200] for x in v[:20]]
        else:
            s = str(v)[:300]

        out[ks] = s

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

    add = getattr(mh, "add_trace", None) or getattr(mh, "write_trace", None) or getattr(mh, "log_trace", None)
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


def _parse_tool_request(req: InterfaceRequest) -> Tuple[Optional[str], Dict[str, Any], bool]:
    """
    Expected shape:
      req.context = { tool_name: str, args: dict, confirm?: bool }
    Approval confirmation MUST be read from context.confirm (not args.confirm).
    """
    ctx = req.context if isinstance(req.context, dict) else {}
    tool_name = ctx.get("tool_name")
    args = ctx.get("args", {})

    confirmed = bool(ctx.get("confirm") is True)
    if not confirmed and isinstance(req.meta, dict):
        confirmed = bool(req.meta.get("confirm") is True)

    if not isinstance(tool_name, str) or not tool_name.strip():
        return None, {}, confirmed

    if not isinstance(args, dict):
        args = {}

    args = dict(args)
    # Never accept secrets through args (meta is the only place)
    for sk in ("master_key", "ssn_master_key"):
        args.pop(sk, None)
    # Never forward confirm into tool args
    args.pop("confirm", None)

    return tool_name.strip(), args, confirmed


def _build_approval_summary(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "tool": tool_name,
        "action": "external_state_change",
        "args_preview": _redact_args(args),
        "note": "This action will affect an external system and requires OWNER approval.",
        "how_to_confirm": {"confirm": True},
    }


def _allowed_from_tool_result(result_ok: bool, result_error: Any) -> bool:
    if result_ok:
        return True
    if isinstance(result_error, dict):
        code = result_error.get("code")
        if isinstance(code, str) and code in _PERMISSION_DENIED_CODES:
            return False
    return True


def _deps_for_run(depsd: Dict[str, Any], *, role: str) -> Dict[str, Any]:
    out = dict(depsd or {})
    out["role"] = _norm_role(role)
    return out


def handle_run_tool(req: InterfaceRequest, deps: Any) -> InterfaceResponse:
    depsd: Dict[str, Any] = deps if isinstance(deps, dict) else {}
    tool_name, args, confirmed = _parse_tool_request(req)

    if tool_name is None:
        return InterfaceResponse(
            ok=False,
            action="run_tool",
            role="GUEST",
            data={},
            error={"code": "BAD_REQUEST", "message": "context.tool_name is required"},
        )

    reg = _get_registry(depsd)

    # Resolve role (do not trust req.role)
    mk = _get_master_key(req)
    scores = None
    resolved_role = "GUEST"
    if mk:
        try:
            scores = verify_owner(mk)
            if is_samson_verified(scores):
                resolved_role = "OWNER"
        except Exception:
            resolved_role = "GUEST"

    # -----------------------------
    # GUEST path
    # -----------------------------
    if resolved_role == "GUEST":
        deps_run = _deps_for_run(depsd, role="GUEST")

        if tool_name in _GUEST_ALLOWLIST:
            spec = reg.get(tool_name)
            if spec is not None and bool(getattr(spec, "state_changing", False)):
                return InterfaceResponse(
                    ok=False,
                    action="run_tool",
                    role="GUEST",
                    data={
                        "identity_verified": False,
                        "role": "GUEST",
                        "allowed": False,
                        "tool": tool_name,
                        "result": None,
                        "error": {
                            "code": "TOOL_STATE_CHANGE_FORBIDDEN",
                            "message": "State-changing tools require OWNER",
                        },
                    },
                    error=None,
                )

            result = reg.run(name=tool_name, role="GUEST", deps=deps_run, args=args)
            return InterfaceResponse(
                ok=bool(result.ok),
                action="run_tool",
                role="GUEST",
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

        spec = reg.get(tool_name)
        if spec is None:
            return InterfaceResponse(
                ok=False,
                action="run_tool",
                role="GUEST",
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

        is_public = bool(getattr(spec, "public", False))
        is_allowed = bool(getattr(spec, "is_role_allowed", lambda r: False)("GUEST"))
        is_state_changing = bool(getattr(spec, "state_changing", False))

        if (not is_public) or (not is_allowed) or is_state_changing:
            return InterfaceResponse(
                ok=False,
                action="run_tool",
                role="GUEST",
                data={
                    "identity_verified": False,
                    "role": "GUEST",
                    "allowed": False,
                    "tool": tool_name,
                    "result": None,
                    "error": {"code": "TOOL_FORBIDDEN", "message": f"GUEST not permitted for tool '{tool_name}'"},
                },
                error=None,
            )

        result = reg.run(name=tool_name, role="GUEST", deps=deps_run, args=args)
        return InterfaceResponse(
            ok=bool(result.ok),
            action="run_tool",
            role="GUEST",
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
    # OWNER path
    # -----------------------------
    deps_run = _deps_for_run(depsd, role="OWNER")

    spec = reg.get(tool_name)
    if spec is None:
        return InterfaceResponse(
            ok=False,
            action="run_tool",
            role="OWNER",
            data={},
            error={"code": "TOOL_NOT_FOUND", "message": tool_name},
        )

    if bool(getattr(spec, "requires_approval", False)) and not confirmed:
        summary = _build_approval_summary(tool_name, args)

        _write_tool_trace(
            deps=deps_run,
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
            role="OWNER",
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

    args2 = dict(args)
    if mk:
        args2["master_key"] = mk  # injected only after approval

    result = reg.run(name=tool_name, role="OWNER", deps=deps_run, args=args2)

    _write_tool_trace(
        deps=deps_run,
        tool_name=tool_name,
        args=args2,
        ok=bool(result.ok),
        err=(result.error if not result.ok else None),
        approval_required=bool(getattr(spec, "requires_approval", False)),
        approved=True,
    )

    try:
        integration = depsd.get("integration")
        if integration is not None:
            from ssn.integration.trace_context import TraceContext
            from ssn.integration.runtime_modes import get_runtime_mode
            import uuid as _uuid

            if get_runtime_mode().value != "legacy":
                # Derive from this InterfaceRequest only — never shared deps trace state.
                tr = TraceContext.extract_or_create(
                    context=req.context if isinstance(getattr(req, "context", None), dict) else {},
                    meta=req.meta if isinstance(getattr(req, "meta", None), dict) else {},
                    deps=depsd,
                    role="OWNER",
                    source="run_tool",
                    runtime_mode=get_runtime_mode().value,
                )
                # Strip master_key from observed args
                safe_args = {
                    k: v
                    for k, v in args.items()
                    if "key" not in str(k).lower() and "secret" not in str(k).lower()
                }
                integration.observe_tool_execution(
                    tool_name=tool_name,
                    args=safe_args,
                    execution_id=str(_uuid.uuid4()),
                    ok=bool(result.ok),
                    result_summary={
                        "ok": bool(result.ok),
                        "error": result.error if not result.ok else None,
                    },
                    trace=tr,
                )
    except Exception:
        pass

    return InterfaceResponse(
        ok=bool(result.ok),
        action="run_tool",
        role="OWNER",
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
