# ssn/interfaces/handlers.py
from __future__ import annotations

import inspect
from typing import Any, Dict, Optional, Callable, List

from ssn.interfaces.contracts import InterfaceRequest, InterfaceResponse, ErrorInfo

# IMPORTANT: module-level imports so tests can patch:
from ssn.identity.owner_verification import verify_owner, is_samson_verified


# -----------------------------
# Helpers
# -----------------------------
_SECRET_KEYS_EXACT = {
    "master_key", "ssn_master_key",
    "api_key", "apikey",
    "token", "access_token", "refresh_token",
    "authorization", "bearer",
    "secret", "password", "passwd",
    "private_key", "privatekey",
    "client_secret",
}
_SECRET_KEY_PREFIXES = ("auth", "bearer", "token", "secret", "password", "private", "access_", "refresh_", "api_key")


def _is_secret_key_name(name: str) -> bool:
    k = (name or "").strip().lower()
    if not k:
        return False
    if k in _SECRET_KEYS_EXACT:
        return True
    return any(k.startswith(p) for p in _SECRET_KEY_PREFIXES)


def _safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _extract_master_key(req: InterfaceRequest) -> Optional[str]:
    """
    Preferred source: req.meta["master_key"]
    Fallbacks: req.context["meta"]["master_key"], req.context["master_key"], req.context["auth"]["master_key"] (legacy)
    """
    if isinstance(req.meta, dict):
        mk = req.meta.get("master_key")
        if isinstance(mk, str) and mk.strip():
            return mk.strip()

    ctx = req.context if isinstance(req.context, dict) else {}

    meta = ctx.get("meta")
    if isinstance(meta, dict):
        mkm = meta.get("master_key")
        if isinstance(mkm, str) and mkm.strip():
            return mkm.strip()

    mk2 = ctx.get("master_key")
    if isinstance(mk2, str) and mk2.strip():
        return mk2.strip()

    auth = ctx.get("auth")
    if isinstance(auth, dict):
        mk3 = auth.get("master_key")
        if isinstance(mk3, str) and mk3.strip():
            return mk3.strip()

    return None


def _resolve_role(master_key: Optional[str]) -> tuple[str, Optional[dict]]:
    """
    Resolve role without trusting the request role.
    Returns (role, scores).
    """
    if not master_key or not isinstance(master_key, str) or not master_key.strip():
        return "GUEST", None
    try:
        scores = verify_owner(master_key)
        if is_samson_verified(scores):
            return "OWNER", scores
        return "GUEST", scores
    except Exception:
        return "GUEST", None


def _sanitize_context(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Hard redaction: ensures no secret credential fields are forwarded into SSN core.
    """
    if not isinstance(context, dict):
        return {}

    clean = dict(context)

    # remove top-level secrets
    for k in list(clean.keys()):
        if _is_secret_key_name(str(k)):
            clean.pop(k, None)

    # remove nested auth secrets
    auth = clean.get("auth")
    if isinstance(auth, dict):
        auth2 = dict(auth)
        for k in list(auth2.keys()):
            if _is_secret_key_name(str(k)):
                auth2.pop(k, None)
        clean["auth"] = auth2

    # remove nested meta secrets
    meta = clean.get("meta")
    if isinstance(meta, dict):
        meta2 = dict(meta)
        for k in list(meta2.keys()):
            if _is_secret_key_name(str(k)):
                meta2.pop(k, None)
        clean["meta"] = meta2

    return clean


def _scrub_secrets(x: Any) -> Any:
    if isinstance(x, dict):
        out = {}
        for k, v in x.items():
            if _is_secret_key_name(str(k)):
                continue
            out[k] = _scrub_secrets(v)
        return out
    if isinstance(x, list):
        return [_scrub_secrets(v) for v in x]
    return x


def _is_registry_like(obj: Any) -> bool:
    if obj is None:
        return False
    for attr in ("get", "run", "list"):
        if not callable(getattr(obj, attr, None)):
            return False
    return True


def _get_tool_registry(deps: Dict[str, Any]):
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
    try:
        from ssn.tools.registry import ToolRegistry  # type: ignore
        from ssn.tools.builtin_tools import register_builtin_tools  # type: ignore
    except Exception:
        return None

    reg3 = ToolRegistry()
    try:
        register_builtin_tools(reg3)
    except Exception:
        pass
    deps["tool_registry"] = reg3
    return reg3


# =====================================================================
# Phase 6.6 — Chat Command Router helpers (OWNER-verified tools via chat)
# =====================================================================

def _tool_requires_approval(reg: Any, tool_name: str) -> bool:
    try:
        spec = reg.get(tool_name)
    except Exception:
        spec = None
    return bool(getattr(spec, "requires_approval", False)) if spec is not None else False


def _maybe_run_tool_plan(
    *,
    text: str,
    ctx: Dict[str, Any],
    deps: Dict[str, Any],
    master_key: Optional[str],
    role: str,
) -> Optional[Dict[str, Any]]:
    """
    If chat text looks like a command, run tool(s) and return a structured payload.
    Otherwise return None.

    Security:
      - Role is resolved by master_key (caller role ignored).
      - Enforces requires_approval via ctx.confirm=True.
      - master_key is injected ONLY into tool args (never into ctx).
    """
    if role != "OWNER":
        return None
    if not master_key or not isinstance(master_key, str) or not master_key.strip():
        return None

    try:
        from ssn.tools.tool_command_router import build_tool_plan  # type: ignore
    except Exception:
        return None

    plan = build_tool_plan(text, ctx)
    if not plan:
        return None

    reg = _get_tool_registry(deps)
    if reg is None:
        return {
            "tool_command": True,
            "ok": False,
            "reason": "tool_registry_missing",
            "plan": [{"tool": c.name, "args": _scrub_secrets(c.args)} for c in plan],
            "results": [],
            "final_message": "Tools unavailable (tool_registry_missing).",
        }

    confirmed = bool(ctx.get("confirm") is True)

    # Block approval-required tools unless confirmed
    blocked: List[dict] = []
    for call in plan:
        if _tool_requires_approval(reg, call.name) and not confirmed:
            blocked.append({"tool": call.name, "args": _scrub_secrets(call.args)})

    if blocked:
        return {
            "tool_command": True,
            "ok": False,
            "reason": "needs_owner_approval",
            "plan": [{"tool": c.name, "args": _scrub_secrets(c.args)} for c in plan],
            "blocked": blocked,
            "final_message": "Approval required. Re-send with context.confirm=True (OWNER only).",
        }

    deps_run = dict(deps or {})
    deps_run["role"] = "OWNER"

    results = []
    for call in plan:
        args = dict(call.args or {})
        # Only tool args get the master_key
        args["master_key"] = master_key

        r = reg.run(name=call.name, role="OWNER", deps=deps_run, args=args)
        results.append(
            {
                "tool": call.name,
                "ok": bool(getattr(r, "ok", False)),
                "data": _scrub_secrets(getattr(r, "data", None)),
                "error": _scrub_secrets(getattr(r, "error", None)),
            }
        )

    ok_count = sum(1 for x in results if x.get("ok"))
    msg = f"Executed {len(results)} tool(s). ok={ok_count}/{len(results)}."

    return {
        "tool_command": True,
        "identity_verified": True,
        "role": "OWNER",
        "allowed": True,
        "plan": [{"tool": c.name, "args": _scrub_secrets(c.args)} for c in plan],
        "results": results,
        "final_message": msg,
    }


# =====================================================================
# Phase 6.5C — Identity + World context injection (OWNER verified)
# =====================================================================

def _build_identity_context(*, master_key: str) -> Dict[str, Any]:
    try:
        from ssn.identity.identity_profile import IdentityProfileStore, verify_profile  # type: ignore
    except Exception:
        return {"available": False, "reason": "identity_profile_module_missing"}

    store = IdentityProfileStore()
    view = store.view()
    if not isinstance(view, dict) or not view.get("available"):
        return {"available": False, "reason": "no_identity_profile"}

    prof = view.get("profile", {})
    if not isinstance(prof, dict):
        return {"available": False, "reason": "invalid_identity_profile"}

    owner_name = str(prof.get("owner_name", "unknown"))
    creator_name = str(prof.get("creator_name", "unknown"))
    system_name = str(prof.get("system_name", "SSN"))
    mission = str(prof.get("mission", ""))

    laws_raw = prof.get("laws", [])
    laws: list[str] = []
    if isinstance(laws_raw, list):
        for x in laws_raw[:8]:
            laws.append(str(x)[:240])

    sig_ok = False
    try:
        sig_ok = bool(verify_profile(prof, master_key))
    except Exception:
        sig_ok = False

    ident = {
        "available": True,
        "system_name": system_name,
        "owner_name": owner_name,
        "creator_name": creator_name,
        "mission": mission[:500],
        "laws": laws,
        "signature_valid": sig_ok,
        "version": str(prof.get("version", "")),
    }

    laws_part = "; ".join(laws[:3]) if laws else "none"
    summary = f"Identity: system={system_name} | owner={owner_name} | creator={creator_name} | laws={laws_part}"
    if len(summary) > 600:
        summary = summary[:599] + "…"
    ident["summary"] = summary
    return ident


def _inject_world_context_if_owner_verified(
    *,
    deps: Dict[str, Any],
    ctx: Dict[str, Any],
    master_key: Optional[str],
    role: str,
) -> Dict[str, Any]:
    base = dict(ctx or {})

    if role != "OWNER":
        return base
    if not master_key or not isinstance(master_key, str) or not master_key.strip():
        return base

    # Identity injection
    try:
        ident = _build_identity_context(master_key=master_key)
        base["identity"] = {k: v for k, v in ident.items() if k != "summary"}
        base["identity_summary"] = str(ident.get("summary", "Identity: unavailable."))
        base["_identity"] = base["identity"]
        base["_identity_summary"] = base["identity_summary"]
    except Exception:
        pass

    orch = deps.get("orchestrator")
    world_model = deps.get("world_model") or (getattr(orch, "world_model", None) if orch else None)

    if world_model is None:
        try:
            from ssn.world.world_model import WorldModel  # type: ignore
            world_model = WorldModel()
        except Exception:
            world_model = None

    if world_model is None or not callable(getattr(world_model, "snapshot", None)):
        base["world"] = {"available": False, "reason": "world_model_not_configured"}
        base["world_summary"] = "World: unavailable (world_model_not_configured)."
        base["_world"] = base["world"]
        base["_world_summary"] = base["world_summary"]
        return base

    provider = deps.get("world_context_provider") or (getattr(orch, "world_context_provider", None) if orch else None)

    try:
        from ssn.world.world_context import WorldContextProvider, WorldContextConfig  # type: ignore
        from ssn.world.world_summary import WorldSummaryNormalizer, WorldSummaryConfig  # type: ignore

        if provider is None:
            provider = WorldContextProvider(
                WorldContextConfig(
                    max_entities=8,
                    max_events=8,
                    max_attr_keys=10,
                    include_events=True,
                )
            )

        summarizer = WorldSummaryNormalizer(
            WorldSummaryConfig(
                max_entities=6,
                max_events=6,
                max_attr_keys=4,
                max_chars=600,
            )
        )

        world_context = provider.build(world_model)
        world_summary = summarizer.summarize(world_context)

        base["world"] = world_context
        base["world_summary"] = world_summary
        base["_world"] = world_context
        base["_world_summary"] = world_summary

        return base
    except Exception:
        return base


# =====================================================================
# Compat call helper
# =====================================================================

def _call_compat(
    fn: Callable[..., Any],
    *,
    user_input: Any,
    role: str,
    context: Dict[str, Any],
) -> Any:
    """
    Calls entrypoints with best-effort compatible signatures.
    IMPORTANT: Never passes master_key into orchestrator/router.
    """
    try:
        sig = inspect.signature(fn)
    except Exception:
        sig = None

    def call_kwargs(kwargs: Dict[str, Any]) -> Any:
        if sig is None:
            return fn(**kwargs)
        params = sig.parameters
        has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
        if has_varkw:
            return fn(**kwargs)
        filtered = {k: v for k, v in kwargs.items() if k in params}
        return fn(**filtered)

    kw_candidates: list[Dict[str, Any]] = [
        {"role": role, "user_input": user_input, "context": context},
        {"user_input": user_input, "role": role, "context": context},
        {"user_input": user_input, "context": context},
        {"user_input": user_input},
        {"message": user_input, "context": context},
        {"message": user_input},
        {"text": user_input, "context": context},
        {"text": user_input},
    ]

    last_type_error: Optional[TypeError] = None
    for kw in kw_candidates:
        try:
            return call_kwargs(kw)
        except TypeError as e:
            last_type_error = e
            continue

    pos_candidates: list[tuple] = [
        (role, user_input, context),
        (role, user_input),
        (user_input, context),
        (user_input,),
        tuple(),
    ]

    for args in pos_candidates:
        try:
            return fn(*args)
        except TypeError as e:
            last_type_error = e
            continue

    if last_type_error is not None:
        raise last_type_error
    raise TypeError("No compatible call signature found.")


# =====================================================================
# Primary handlers
# =====================================================================

def handle_think(req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
    orchestrator = deps.get("orchestrator")
    router = deps.get("brain_router")

    mk = _extract_master_key(req)
    role, _scores = _resolve_role(mk)
    ctx = _sanitize_context(req.context)

    # Owner-only context injection (identity + world)
    try:
        ctx = _inject_world_context_if_owner_verified(deps=deps, ctx=ctx, master_key=mk, role=role)
    except Exception:
        pass

    # Phase 6.6 — Chat Command Router (approval-safe now)
    try:
        routed = _maybe_run_tool_plan(text=str(req.user_input or ""), ctx=ctx, deps=deps, master_key=mk, role=role)
        if isinstance(routed, dict):
            return InterfaceResponse(ok=bool(routed.get("ok", True)), action=req.action, role=role, data=_safe_dict(_scrub_secrets(routed)))
    except Exception:
        pass

    # Prefer orchestrator entrypoints
    if orchestrator is not None:
        for m in ("handle_request", "run", "process", "handle", "think"):
            fn = getattr(orchestrator, m, None)
            if callable(fn):
                try:
                    out = _call_compat(fn, user_input=req.user_input, role=role, context=ctx)
                    return InterfaceResponse(ok=True, action=req.action, role=role, data=_safe_dict(_scrub_secrets(out)))
                except Exception as e:
                    return InterfaceResponse(
                        ok=False,
                        action=req.action,
                        role=role,
                        error=ErrorInfo(code="ORCH_RUNTIME_ERROR", message=str(e)),
                    )

        return InterfaceResponse(
            ok=False,
            action=req.action,
            role=role,
            error=ErrorInfo(code="ORCH_ENTRYPOINT_MISSING", message="Orchestrator has no compatible entrypoint."),
        )

    # Fallback to router
    if router is not None:
        fn = getattr(router, "route", None)
        if callable(fn):
            try:
                out = _call_compat(fn, user_input=req.user_input, role=role, context=ctx)
                return InterfaceResponse(ok=True, action=req.action, role=role, data=_safe_dict(_scrub_secrets(out)))
            except Exception as e:
                return InterfaceResponse(
                    ok=False,
                    action=req.action,
                    role=role,
                    error=ErrorInfo(code="ROUTER_RUNTIME_ERROR", message=str(e)),
                )

    return InterfaceResponse(
        ok=False,
        action=req.action,
        role=role,
        error=ErrorInfo(code="NO_BRAIN_AVAILABLE", message="No orchestrator or brain_router available."),
    )


def handle_explain_state(req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
    memory_hub = deps.get("memory_hub")
    safety_monitor = deps.get("safety_monitor")
    policy_engine = deps.get("policy_engine")

    role = "GUEST"
    try:
        mk = _extract_master_key(req)
        role, _ = _resolve_role(mk)
    except Exception:
        role = "GUEST"

    state: Dict[str, Any] = {"phase": "4.0", "interfaces": "enabled"}

    if safety_monitor is not None:
        snapshot = getattr(safety_monitor, "snapshot", None)
        if callable(snapshot):
            state["safety"] = snapshot()
        else:
            state["safety"] = {
                "has_monitor": True,
                "methods": [
                    m
                    for m in ("allow_internal_reflection", "allow_internal_analysis", "allow_internal_thought")
                    if callable(getattr(safety_monitor, m, None))
                ],
            }

    if policy_engine is not None:
        snap = getattr(policy_engine, "snapshot", None)
        if callable(snap):
            state["policy"] = snap()
        else:
            state["policy"] = {"has_engine": True}

    if memory_hub is not None:
        get_summary = getattr(memory_hub, "get_summary", None)
        if callable(get_summary):
            state["memory"] = get_summary()
        else:
            get_tr = getattr(memory_hub, "get_recent_traces", None)
            get_ep = getattr(memory_hub, "get_recent_episodic", None)
            traces = get_tr(limit=50) if callable(get_tr) else []
            epis = get_ep(limit=20) if callable(get_ep) else []
            state["memory"] = {"recent_traces": len(traces or []), "recent_episodic": len(epis or [])}

    return InterfaceResponse(ok=True, action=req.action, role=role, data=_safe_dict(_scrub_secrets(state)))


def handle_summarize_memory(req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
    memory_hub = deps.get("memory_hub")

    mk = _extract_master_key(req)
    role, _ = _resolve_role(mk)

    if memory_hub is None:
        return InterfaceResponse(
            ok=False,
            action=req.action,
            role=role,
            error=ErrorInfo(code="NO_MEMORY_HUB", message="MemoryHub not available."),
        )

    get_tr = getattr(memory_hub, "get_recent_traces", None)
    get_ep = getattr(memory_hub, "get_recent_episodic", None)

    meta = req.meta if isinstance(req.meta, dict) else {}
    traces = get_tr(limit=int(meta.get("trace_limit", 30))) if callable(get_tr) else []
    epis = get_ep(limit=int(meta.get("episodic_limit", 10))) if callable(get_ep) else []

    def extract_type(item: Any) -> Optional[str]:
        if isinstance(item, dict):
            payload = item.get("payload", item)
            if isinstance(payload, dict):
                t = payload.get("type")
                return t if isinstance(t, str) else None
        return None

    types: Dict[str, int] = {}
    for it in traces or []:
        t = extract_type(it) or "unknown"
        types[t] = types.get(t, 0) + 1

    data = {
        "traces_count": len(traces or []),
        "episodic_count": len(epis or []),
        "trace_type_histogram": types,
    }

    return InterfaceResponse(ok=True, action=req.action, role=role, data=_safe_dict(_scrub_secrets(data)))


def handle_suggest(req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
    suggestion_engine = deps.get("suggestion_engine")

    mk = _extract_master_key(req)
    role, _ = _resolve_role(mk)

    if suggestion_engine is not None:
        fn = getattr(suggestion_engine, "run_once", None)
        if callable(fn):
            meta = req.meta if isinstance(req.meta, dict) else {}
            out = fn(trace_limit=int(meta.get("trace_limit", 150)), write_trace=True)
            return InterfaceResponse(ok=True, action=req.action, role=role, data=_safe_dict(_scrub_secrets(out)))

    return InterfaceResponse(
        ok=True,
        action=req.action,
        role=role,
        data={"status": "no_suggestion_engine", "suggestion_count": 0, "requires_owner_ack": True},
    )


HANDLERS = {
    "think": handle_think,
    "explain_state": handle_explain_state,
    "summarize_memory": handle_summarize_memory,
    "suggest": handle_suggest,
}
