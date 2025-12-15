# ssn/interfaces/handlers.py

from __future__ import annotations

import inspect
from typing import Any, Dict, Optional, Callable

from ssn.interfaces.contracts import InterfaceRequest, InterfaceResponse, ErrorInfo

# IMPORTANT: module-level imports so tests can patch:
# patch("ssn.interfaces.handlers.verify_owner", ...)
from ssn.identity.owner_verification import verify_owner, is_samson_verified


def _safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _extract_master_key(req: InterfaceRequest) -> Optional[str]:
    """
    Preferred source: req.meta["master_key"]
    Fallbacks: req.context["master_key"], req.context["auth"]["master_key"]
    """
    if isinstance(req.meta, dict):
        mk = req.meta.get("master_key")
        if isinstance(mk, str) and mk.strip():
            return mk.strip()

    ctx = req.context if isinstance(req.context, dict) else {}
    mk2 = ctx.get("master_key")
    if isinstance(mk2, str) and mk2.strip():
        return mk2.strip()

    auth = ctx.get("auth")
    if isinstance(auth, dict):
        mk3 = auth.get("master_key")
        if isinstance(mk3, str) and mk3.strip():
            return mk3.strip()

    return None


def _sanitize_context(context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Hard redaction: ensures no secret credential fields are forwarded into SSN core.
    """
    if not isinstance(context, dict):
        return {}

    clean = dict(context)

    # remove top-level master_key
    if "master_key" in clean:
        clean.pop("master_key", None)

    # remove nested auth.master_key
    auth = clean.get("auth")
    if isinstance(auth, dict):
        auth2 = dict(auth)
        if "master_key" in auth2:
            auth2.pop("master_key", None)
        clean["auth"] = auth2

    return clean


def _inject_world_context_if_owner_verified(
    *,
    req: InterfaceRequest,
    deps: Dict[str, Any],
    ctx: Dict[str, Any],
    master_key: Optional[str],
) -> Dict[str, Any]:
    """
    Inject bounded world context into cognition context ONLY if owner is verified.

    Writes both modern keys and legacy keys for compatibility:
      ctx["world"] / ctx["world_summary"]
      ctx["_world"] / ctx["_world_summary"]
    """
    base = dict(ctx or {})

    if not master_key or not isinstance(master_key, str) or not master_key.strip():
        return base

    # Verify ownership using master key (do NOT trust claimed role)
    scores = verify_owner(master_key)
    if not is_samson_verified(scores):
        return base

    # Resolve world_model:
    # 1) deps["world_model"]
    # 2) orchestrator.world_model
    # 3) load persisted WorldModel() from disk
    world_model = deps.get("world_model")
    orch = deps.get("orchestrator")

    if world_model is None and orch is not None:
        world_model = getattr(orch, "world_model", None)

    if world_model is None:
        try:
            from ssn.world.world_model import WorldModel  # type: ignore
            world_model = WorldModel()  # loads ssn/data/world_model.json
        except Exception:
            world_model = None

    if world_model is None or not callable(getattr(world_model, "snapshot", None)):
        base["world"] = {"available": False, "reason": "world_model_not_configured"}
        base["world_summary"] = "World: unavailable (world_model_not_configured)."
        base["_world"] = base["world"]
        base["_world_summary"] = base["world_summary"]
        return base

    provider = deps.get("world_context_provider")
    if provider is None and orch is not None:
        provider = getattr(orch, "world_context_provider", None)

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
        # Never break cognition due to world injection failure
        return base


def _call_compat(
    fn: Callable[..., Any],
    *,
    master_key: Optional[str],
    user_input: Any,
    role: str,
    context: Dict[str, Any],
) -> Any:
    """
    Calls entrypoints with best-effort compatible signatures.
    Critically: if 'master_key' is accepted, it is passed explicitly to avoid arg shifting.
    """
    try:
        sig = inspect.signature(fn)
    except Exception:
        sig = None

    def accepts(name: str) -> bool:
        if sig is None:
            return True
        params = sig.parameters
        if name in params:
            return True
        return any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())

    def call_kwargs(kwargs: Dict[str, Any]) -> Any:
        if sig is None:
            return fn(**kwargs)
        params = sig.parameters
        has_varkw = any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values())
        if has_varkw:
            return fn(**kwargs)
        filtered = {k: v for k, v in kwargs.items() if k in params}
        return fn(**filtered)

    kw_candidates: list[Dict[str, Any]] = []

    if accepts("master_key"):
        kw_candidates += [
            {"master_key": master_key, "user_input": user_input, "context": context},
            {"master_key": master_key, "user_input": user_input},
            {"master_key": master_key, "message": user_input, "context": context},
            {"master_key": master_key, "message": user_input},
            {"master_key": master_key, "text": user_input, "context": context},
            {"master_key": master_key, "text": user_input},
        ]

    kw_candidates += [
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

    pos_candidates: list[tuple] = []
    if accepts("master_key"):
        pos_candidates += [
            (master_key, user_input, context),
            (master_key, user_input),
            (master_key,),
        ]
    pos_candidates += [
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


def handle_think(req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
    """
    Internal cognition. Prefers Orchestrator; falls back to BrainRouter.

    Inject bounded world context for VERIFIED OWNER (by master key).
    """
    orchestrator = deps.get("orchestrator")
    router = deps.get("brain_router")

    mk = _extract_master_key(req)
    ctx = _sanitize_context(req.context)

    try:
        ctx = _inject_world_context_if_owner_verified(req=req, deps=deps, ctx=ctx, master_key=mk)
    except Exception:
        pass

    if orchestrator is not None:
        for m in ("handle_request", "run", "process", "handle", "think"):
            fn = getattr(orchestrator, m, None)
            if callable(fn):
                try:
                    out = _call_compat(
                        fn,
                        master_key=mk,
                        user_input=req.user_input,
                        role=req.role,
                        context=ctx,
                    )
                    return InterfaceResponse(ok=True, action=req.action, role=req.role, data=_safe_dict(out))
                except Exception as e:
                    return InterfaceResponse(
                        ok=False,
                        action=req.action,
                        role=req.role,
                        error=ErrorInfo(code="ORCH_RUNTIME_ERROR", message=str(e)),
                    )

        return InterfaceResponse(
            ok=False,
            action=req.action,
            role=req.role,
            error=ErrorInfo(code="ORCH_ENTRYPOINT_MISSING", message="Orchestrator has no compatible entrypoint."),
        )

    if router is not None:
        fn = getattr(router, "route", None)
        if callable(fn):
            try:
                out = _call_compat(
                    fn,
                    master_key=mk,
                    user_input=req.user_input,
                    role=req.role,
                    context=ctx,
                )
                return InterfaceResponse(ok=True, action=req.action, role=req.role, data=_safe_dict(out))
            except Exception as e:
                return InterfaceResponse(
                    ok=False,
                    action=req.action,
                    role=req.role,
                    error=ErrorInfo(code="ROUTER_RUNTIME_ERROR", message=str(e)),
                )

    return InterfaceResponse(
        ok=False,
        action=req.action,
        role=req.role,
        error=ErrorInfo(code="NO_BRAIN_AVAILABLE", message="No orchestrator or brain_router available."),
    )


def handle_explain_state(req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
    memory_hub = deps.get("memory_hub")
    safety_monitor = deps.get("safety_monitor")
    policy_engine = deps.get("policy_engine")

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

    return InterfaceResponse(ok=True, action=req.action, role=req.role, data=state)


def handle_summarize_memory(req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
    memory_hub = deps.get("memory_hub")
    if memory_hub is None:
        return InterfaceResponse(
            ok=False,
            action=req.action,
            role=req.role,
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

    return InterfaceResponse(ok=True, action=req.action, role=req.role, data=data)


def handle_suggest(req: InterfaceRequest, deps: Dict[str, Any]) -> InterfaceResponse:
    suggestion_engine = deps.get("suggestion_engine")

    if suggestion_engine is not None:
        fn = getattr(suggestion_engine, "run_once", None)
        if callable(fn):
            meta = req.meta if isinstance(req.meta, dict) else {}
            out = fn(trace_limit=int(meta.get("trace_limit", 150)), write_trace=True)
            return InterfaceResponse(ok=True, action=req.action, role=req.role, data=_safe_dict(out))

    return InterfaceResponse(
        ok=True,
        action=req.action,
        role=req.role,
        data={"status": "no_suggestion_engine", "suggestion_count": 0, "requires_owner_ack": True},
    )


HANDLERS = {
    "think": handle_think,
    "explain_state": handle_explain_state,
    "summarize_memory": handle_summarize_memory,
    "suggest": handle_suggest,
}
