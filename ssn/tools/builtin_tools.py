# ssn/tools/builtin_tools.py
from __future__ import annotations

import importlib
from typing import Any, Dict, Optional, List

from ssn.tools.contracts import ToolSpec
from ssn.tools.registry import ToolRegistry

from ssn.tools.net_tools import register_net_tools
from ssn.tools.media_tools import register_media_tools
from ssn.tools.speech_tools import register_speech_tools
from ssn.tools.memory_pending_tools import register_memory_pending_tools
from ssn.tools.knowledge_tools import register_knowledge_tools


def _safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _get_memory_hub(deps: Dict[str, Any]):
    """
    Return the wired MemoryHub instance.

    IMPORTANT:
    - Do NOT instantiate a new MemoryHub here. That creates split-brain memory where
      tools write to a different instance than the runtime/orchestrator uses.
    """
    mh = deps.get("memory_hub")
    if mh is not None:
        return mh

    orch = deps.get("orchestrator")
    if orch is not None:
        mh = getattr(orch, "memory_hub", None) or getattr(orch, "memory", None)
        if mh is not None:
            return mh

    return None


# =========================================================
# Best-effort tool module registration (minimal + safe)
# =========================================================
def _try_import(module: str):
    try:
        # More predictable than __import__ for dotted modules
        return importlib.import_module(module)
    except Exception:
        return None


def _try_register_toolspec(reg: ToolRegistry, spec: Any) -> bool:
    """
    Register a ToolSpec if present, but do it idempotently.

    Your ToolRegistry.register() overwrites by name. For safety in composed
    registrations, we skip if a tool of the same name already exists.
    """
    if not isinstance(spec, ToolSpec):
        return False

    name = getattr(spec, "name", None)
    if not isinstance(name, str) or not name.strip():
        return False

    # Idempotent: do not override existing registrations silently
    try:
        if reg.get(name) is not None:
            return True
    except Exception:
        # If reg.get() ever changes, fall through to register attempt
        pass

    try:
        reg.register(spec)
        return True
    except Exception:
        return False


def _register_if_present(
    reg: ToolRegistry,
    *,
    module: str,
    register_fn: Optional[str] = None,
    spec_names: Optional[List[str]] = None,
) -> None:
    """
    Registers tools from a module in a resilient way without forcing strict naming.

    Supports either:
      - module.<register_fn>(reg)         (preferred)
      - module.<spec_name> == ToolSpec    (fallback)

    Also supports a last-resort scan for ToolSpec-like constants:
      *_T / *_TOOL / *_SPEC
    """
    m = _try_import(module)
    if m is None:
        return

    if register_fn:
        fn = getattr(m, register_fn, None)
        if callable(fn):
            try:
                fn(reg)
                return
            except Exception:
                # fall through to ToolSpec constants
                pass

    for name in (spec_names or []):
        if _try_register_toolspec(reg, getattr(m, name, None)):
            return

    # Last resort: scan for any ToolSpec constants and register them
    try:
        for attr in dir(m):
            if attr.endswith("_T") or attr.endswith("_TOOL") or attr.endswith("_SPEC"):
                v = getattr(m, attr, None)
                _try_register_toolspec(reg, v)
    except Exception:
        return


def register_builtin_tools(reg: ToolRegistry) -> None:
    # =========================================================
    # Core tools
    # =========================================================

    def tools_list(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        """
        Canonical behavior:
          - OWNER => full list (reg.list())
          - GUEST => public-only list (reg.list_public(role="GUEST"))

        IMPORTANT IMPLEMENTATION NOTE:
        - Tool handlers do not receive the 'role' parameter from ToolRegistry.run(...)
          directly.
        - In your gateway handler, OWNER requests inject args["master_key"] AFTER
          verification. GUEST requests never receive master_key.
        - Therefore: presence of args["master_key"] is a reliable signal for OWNER.
        """
        mk = args.get("master_key")
        if isinstance(mk, str) and mk.strip():
            return {"scope": "full", "tools": reg.list()}
        return {"scope": "public", "tools": reg.list_public(role="GUEST")}

    # Allow both roles to call tools.list:
    # - OWNER gets full list (via injected master_key)
    # - GUEST gets public-only list
    reg.register(
        ToolSpec(
            name="tools.list",
            description="List tools. OWNER gets full list; GUEST gets public-only list.",
            required_role="GUEST",
            allowed_roles=("OWNER", "GUEST"),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=60,
            input_schema={},
            handler=tools_list,
        )
    )

    reg.register(
        ToolSpec(
            name="tools.public_list",
            description="List guest-safe public tools (GUEST-allowed).",
            required_role="GUEST",
            allowed_roles=("OWNER", "GUEST"),
            public=True,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=120,
            input_schema={},
            handler=lambda deps, args: {"scope": "public", "tools": reg.list_public(role="GUEST")},
        )
    )

    # =========================================================
    # World tools
    # =========================================================
    def world_read(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        from ssn.interfaces.contracts import InterfaceRequest
        from ssn.interfaces.handlers_world import handle_world

        ctx = {
            "max_entities": int(args.get("max_entities", 8) or 8),
            "max_events": int(args.get("max_events", 8) or 8),
            "include_events": bool(args.get("include_events", True)),
        }

        mk = args.get("master_key")
        req = InterfaceRequest(
            action="world",
            role="OWNER",
            user_input="",
            context=ctx,
            meta={"master_key": mk} if mk else {},
        )
        resp = handle_world(req, deps)
        return _safe_dict(getattr(resp, "data", {}))

    reg.register(
        ToolSpec(
            name="world.read",
            description="Return bounded world context + summary (OWNER-only).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=120,
            input_schema={"max_entities": "int", "max_events": "int", "include_events": "bool"},
            handler=world_read,
        )
    )

    def world_sense_tick(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        from ssn.interfaces.contracts import InterfaceRequest
        from ssn.interfaces.handlers_sense_tick import handle_sense_tick

        mk = args.get("master_key")
        ctx = {
            "events": args.get("events", []),
            "max_events": int(args.get("max_events", 25) or 25),
        }

        req = InterfaceRequest(
            action="sense_tick",
            role="OWNER",
            user_input="",
            context=ctx,
            meta={"master_key": mk} if mk else {},
        )
        resp = handle_sense_tick(req, deps)
        return _safe_dict(getattr(resp, "data", {}))

    reg.register(
        ToolSpec(
            name="world.sense_tick",
            description="Run one bounded perception tick (OWNER-only, state-changing).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=True,
            external_effect=False,
            max_calls_per_minute=3,
            input_schema={"events": "list", "max_events": "int"},
            handler=world_sense_tick,
        )
    )

    # =========================================================
    # Memory summary
    # =========================================================
    def memory_summary(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        from ssn.interfaces.contracts import InterfaceRequest
        from ssn.interfaces.handlers import handle_summarize_memory

        req = InterfaceRequest(
            action="summarize_memory",
            role="OWNER",
            user_input="",
            context={},
            meta={
                "trace_limit": int(args.get("trace_limit", 30) or 30),
                "episodic_limit": int(args.get("episodic_limit", 10) or 10),
            },
        )
        resp = handle_summarize_memory(req, deps)
        return _safe_dict(getattr(resp, "data", {}))

    reg.register(
        ToolSpec(
            name="memory.summary",
            description="Summarize recent memory traces/episodic entries (OWNER-only).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=60,
            input_schema={"trace_limit": "int", "episodic_limit": "int"},
            handler=memory_summary,
        )
    )

    # =========================================================
    # Semantic facts
    # =========================================================
    def memory_fact_set(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        mh = _get_memory_hub(deps)
        if mh is None:
            return {"ok": False, "reason": "no_memory_hub"}

        key = args.get("key")
        if not isinstance(key, str) or not key.strip():
            return {"ok": False, "reason": "key_required"}

        k = key.strip()
        if k.lower() in {"master_key", "ssn_master_key"}:
            return {"ok": False, "reason": "refuse_store_secret_key"}

        mh.remember_fact(k, args.get("value"))
        return {"ok": True, "status": "stored", "key": k}

    reg.register(
        ToolSpec(
            name="memory.fact.set",
            description="Store a semantic fact (OWNER-only, state-changing).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=True,
            external_effect=False,
            max_calls_per_minute=30,
            input_schema={"key": "str", "value": "any"},
            handler=memory_fact_set,
        )
    )

    def memory_fact_get(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        mh = _get_memory_hub(deps)
        if mh is None:
            return {"ok": False, "reason": "no_memory_hub"}

        key = args.get("key")
        if not isinstance(key, str) or not key.strip():
            return {"ok": False, "reason": "key_required"}

        k = key.strip()
        val = mh.recall_fact(k)
        return {"ok": True, "key": k, "found": val is not None, "value": val}

    reg.register(
        ToolSpec(
            name="memory.fact.get",
            description="Get a semantic fact by key (OWNER-only).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=120,
            input_schema={"key": "str"},
            handler=memory_fact_get,
        )
    )

    def memory_fact_list(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        mh = _get_memory_hub(deps)
        if mh is None:
            return {"ok": False, "reason": "no_memory_hub"}

        facts = mh.recall_all_facts() or {}
        limit = max(0, min(int(args.get("limit", 200) or 200), 1000))
        keys = sorted(map(str, facts.keys()))[:limit]
        return {"ok": True, "count": len(facts), "returned": len(keys), "facts": {k: facts[k] for k in keys}}

    reg.register(
        ToolSpec(
            name="memory.fact.list",
            description="List semantic facts (bounded) (OWNER-only).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=60,
            input_schema={"limit": "int"},
            handler=memory_fact_list,
        )
    )

    def memory_fact_delete(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        mh = _get_memory_hub(deps)
        if mh is None:
            return {"ok": False, "reason": "no_memory_hub"}

        key = args.get("key")
        if not isinstance(key, str) or not key.strip():
            return {"ok": False, "reason": "key_required"}

        mh.forget_fact(key.strip())
        return {"ok": True, "status": "deleted", "key": key.strip()}

    reg.register(
        ToolSpec(
            name="memory.fact.delete",
            description="Delete a semantic fact (OWNER-only, state-changing).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=True,
            external_effect=False,
            max_calls_per_minute=30,
            input_schema={"key": "str"},
            handler=memory_fact_delete,
        )
    )

    # =========================================================
    # Safety & Policy
    # =========================================================
    def safety_status(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        mon = deps.get("safety_monitor")
        if mon is None:
            return {"available": False}
        snap = getattr(mon, "snapshot", None)
        return snap() if callable(snap) else {"available": True}

    reg.register(
        ToolSpec(
            name="safety.status",
            description="Return safety monitor snapshot (OWNER-only).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=120,
            input_schema={},
            handler=safety_status,
        )
    )

    def policy_snapshot(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        pe = deps.get("policy_engine")
        if pe is None:
            return {"available": False}
        snap = getattr(pe, "snapshot", None)
        return snap() if callable(snap) else {"available": True}

    reg.register(
        ToolSpec(
            name="policy.snapshot",
            description="Return policy engine snapshot (OWNER-only).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=120,
            input_schema={},
            handler=policy_snapshot,
        )
    )

    # =========================================================
    # Identity
    # =========================================================
    from ssn.tools.identity_tools import identity_view_tool, identity_enroll_tool

    reg.register(
        ToolSpec(
            name="identity.view",
            description="View the persisted identity profile (OWNER-only).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=60,
            input_schema={},
            handler=identity_view_tool,
        )
    )

    reg.register(
        ToolSpec(
            name="identity.enroll",
            description="Enroll or overwrite the identity profile (OWNER-only, state-changing).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=True,
            external_effect=False,
            max_calls_per_minute=5,
            input_schema={
                "owner_name": "str",
                "creator_name": "str",
                "system_name": "str",
                "mission": "str",
                "laws": "list[str]",
                "force": "bool",
            },
            handler=identity_enroll_tool,
        )
    )

    # =========================================================
    # Episodic events
    # =========================================================
    from ssn.tools.memory_event_tools import (
        memory_event_add_tool,
        memory_event_recent_tool,
        memory_event_search_tool,
    )

    reg.register(
        ToolSpec(
            name="memory.event.add",
            description="Log an episodic event (OWNER-only, state-changing).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=True,
            external_effect=False,
            max_calls_per_minute=60,
            input_schema={"event_type": "str", "actor": "str", "details": "dict"},
            handler=memory_event_add_tool,
        )
    )

    reg.register(
        ToolSpec(
            name="memory.event.recent",
            description="Get recent episodic events (bounded) (OWNER-only).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=120,
            input_schema={"limit": "int"},
            handler=memory_event_recent_tool,
        )
    )

    reg.register(
        ToolSpec(
            name="memory.event.search",
            description="Search episodic events (bounded) (OWNER-only).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=120,
            input_schema={"query": "str", "limit": "int"},
            handler=memory_event_search_tool,
        )
    )

    # =========================================================
    # Trace inspection
    # =========================================================
    from ssn.tools.trace_tools import (
        memory_trace_recent_tool,
        memory_trace_search_tool,
        memory_trace_types_tool,
    )

    reg.register(
        ToolSpec(
            name="memory.trace.recent",
            description="Return recent traces (bounded) (OWNER-only).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=120,
            input_schema={"limit": "int"},
            handler=memory_trace_recent_tool,
        )
    )

    reg.register(
        ToolSpec(
            name="memory.trace.types",
            description="Histogram of trace payload types (OWNER-only).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=120,
            input_schema={"limit": "int"},
            handler=memory_trace_types_tool,
        )
    )

    reg.register(
        ToolSpec(
            name="memory.trace.search",
            description="Search recent traces by substring match (bounded) (OWNER-only).",
            required_role="OWNER",
            allowed_roles=("OWNER",),
            public=False,
            state_changing=False,
            external_effect=False,
            max_calls_per_minute=120,
            input_schema={"query": "str", "limit": "int", "scan_limit": "int"},
            handler=memory_trace_search_tool,
        )
    )

    # =========================================================
    # Pending memory proposals (disk-canonical)
    # =========================================================
    register_memory_pending_tools(reg)

    # =========================================================
    # Phase 7.2 — Network search tool (read-only, bounded)
    # =========================================================
    register_net_tools(reg)

    # =========================================================
    # Phase 7.3 — Research pipeline tools (composed, read-only)
    #   REQUIRED for: research.answer
    # =========================================================
    _register_if_present(
        reg,
        module="ssn.tools.net_fetch",
        register_fn="register_net_fetch_tools",
        spec_names=["NET_FETCH_T", "NET_FETCH_TOOL", "NET_FETCH_SPEC"],
    )
    _register_if_present(
        reg,
        module="ssn.tools.net_sanitize",
        register_fn="register_net_sanitize_tools",
        spec_names=["NET_SANITIZE_T", "NET_SANITIZE_TOOL", "NET_SANITIZE_SPEC"],
    )
    _register_if_present(
        reg,
        module="ssn.tools.net_cite",
        register_fn="register_net_cite_tools",
        spec_names=["NET_CITE_T", "NET_CITE_TOOL", "NET_CITE_SPEC"],
    )
    _register_if_present(
        reg,
        module="ssn.tools.research_answer",
        register_fn="register_research_tools",
        spec_names=["RESEARCH_ANSWER_T", "RESEARCH_ANSWER_TOOL", "RESEARCH_ANSWER_SPEC"],
    )

    # =========================================================
    # Phase 7.3 — Media generation tools (read-only)
    # =========================================================
    register_media_tools(reg)

    # =========================================================
    # Phase 7.4 — Speech interface tools (approval-gated)
    # =========================================================
    register_speech_tools(reg)

    # =========================================================
    # Knowledge tools (promotion + search)
    # =========================================================
    register_knowledge_tools(reg)
