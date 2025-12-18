# ssn/tools/builtin_tools.py

from __future__ import annotations

from typing import Any, Dict

from ssn.interfaces.contracts import InterfaceRequest
from ssn.tools.contracts import ToolSpec
from ssn.tools.registry import ToolRegistry


def _safe_dict(x: Any) -> Dict[str, Any]:
    return x if isinstance(x, dict) else {}


def _get_memory_hub(deps: Dict[str, Any]):
    """
    Prefer wired deps["memory_hub"].
    Fallback to orchestrator.memory_hub or orchestrator.memory.
    Final fallback: construct MemoryHub() (best-effort).
    """
    mh = deps.get("memory_hub")
    if mh is not None:
        return mh

    orch = deps.get("orchestrator")
    if orch is not None:
        mh = getattr(orch, "memory_hub", None) or getattr(orch, "memory", None)
        if mh is not None:
            return mh

    try:
        from ssn.memory.memory_hub import MemoryHub  # type: ignore
        return MemoryHub()
    except Exception:
        return None


def register_builtin_tools(reg: ToolRegistry) -> None:
    # Tool: list tools
    reg.register(
        ToolSpec(
            name="tools.list",
            description="List all available tools (OWNER-only by default).",
            required_role="OWNER",
            state_changing=False,
            input_schema={},
            handler=lambda deps, args: {"tools": reg.list()},
        )
    )

    # Tool: world.read (wrap existing world handler)
    def world_read(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
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
            state_changing=False,
            input_schema={"max_entities": "int", "max_events": "int", "include_events": "bool"},
            handler=world_read,
        )
    )

    # Tool: world.sense_tick (wrap existing sense_tick handler)
    def world_sense_tick(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        from ssn.interfaces.handlers_sense_tick import handle_sense_tick

        mk = args.get("master_key")
        ctx = {"events": args.get("events", []), "max_events": int(args.get("max_events", 25) or 25)}
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
            state_changing=True,
            input_schema={"events": "list", "max_events": "int"},
            handler=world_sense_tick,
        )
    )

    # Tool: memory.summary (wrap existing handler)
    def memory_summary(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
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
            state_changing=False,
            input_schema={"trace_limit": "int", "episodic_limit": "int"},
            handler=memory_summary,
        )
    )

    # -------------------------
    # Phase 6.6B — Semantic facts (teaching / learning)
    # -------------------------

    def memory_fact_set(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        mh = _get_memory_hub(deps)
        if mh is None:
            return {"ok": False, "reason": "no_memory_hub"}

        key = args.get("key")
        if not isinstance(key, str) or not key.strip():
            return {"ok": False, "reason": "key_required"}

        # Any JSON type is acceptable as value
        value = args.get("value", None)

        # Do not allow storing secrets accidentally
        if key.strip().lower() in {"master_key", "ssn_master_key"}:
            return {"ok": False, "reason": "refuse_store_secret_key"}

        mh.remember_fact(key.strip(), value)
        return {"ok": True, "status": "stored", "key": key.strip()}

    reg.register(
        ToolSpec(
            name="memory.fact.set",
            description="Store a semantic fact (OWNER-only, state-changing).",
            required_role="OWNER",
            state_changing=True,
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

        val = mh.recall_fact(key.strip())
        found = val is not None
        return {"ok": True, "key": key.strip(), "found": found, "value": val}

    reg.register(
        ToolSpec(
            name="memory.fact.get",
            description="Get a semantic fact by key (OWNER-only).",
            required_role="OWNER",
            state_changing=False,
            input_schema={"key": "str"},
            handler=memory_fact_get,
        )
    )

    def memory_fact_list(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        mh = _get_memory_hub(deps)
        if mh is None:
            return {"ok": False, "reason": "no_memory_hub"}

        facts = mh.recall_all_facts()
        facts = facts if isinstance(facts, dict) else {}

        # Bounded listing (avoid dumping huge stores)
        limit = int(args.get("limit", 200) or 200)
        if limit < 0:
            limit = 0
        if limit > 1000:
            limit = 1000

        keys = sorted([str(k) for k in facts.keys()])
        keys = keys[:limit]

        out = {k: facts.get(k) for k in keys}
        return {"ok": True, "count": len(facts), "returned": len(out), "facts": out}

    reg.register(
        ToolSpec(
            name="memory.fact.list",
            description="List semantic facts (bounded) (OWNER-only).",
            required_role="OWNER",
            state_changing=False,
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
            state_changing=True,
            input_schema={"key": "str"},
            handler=memory_fact_delete,
        )
    )

    # Tool: safety.status
    def safety_status(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        mon = deps.get("safety_monitor")
        if mon is None:
            return {"available": False, "reason": "no_safety_monitor"}
        snap = getattr(mon, "snapshot", None)
        if callable(snap):
            out = snap()
            return out if isinstance(out, dict) else {"snapshot": out}
        return {"available": True, "methods": [m for m in dir(mon) if m.startswith("allow_")]}

    reg.register(
        ToolSpec(
            name="safety.status",
            description="Return safety monitor snapshot (OWNER-only).",
            required_role="OWNER",
            state_changing=False,
            input_schema={},
            handler=safety_status,
        )
    )

    # Tool: policy.snapshot
    def policy_snapshot(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
        pe = deps.get("policy_engine")
        if pe is None:
            return {"available": False, "reason": "no_policy_engine"}
        snap = getattr(pe, "snapshot", None)
        if callable(snap):
            out = snap()
            return out if isinstance(out, dict) else {"snapshot": out}
        return {"available": True, "has_engine": True}

    reg.register(
        ToolSpec(
            name="policy.snapshot",
            description="Return policy engine snapshot (OWNER-only).",
            required_role="OWNER",
            state_changing=False,
            input_schema={},
            handler=policy_snapshot,
        )
    )
