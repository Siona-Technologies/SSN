from __future__ import annotations

from typing import Any, Dict, List, Optional


def _get_memory_hub(deps: Dict[str, Any]):
    """
    Best-effort resolve MemoryHub from deps / orchestrator.
    """
    hub = deps.get("memory_hub")
    if hub is not None:
        return hub

    orch = deps.get("orchestrator")
    if orch is not None:
        # common attribute names across versions
        for name in ("memory_hub", "memory"):
            h = getattr(orch, name, None)
            if h is not None:
                return h

    return None


def memory_event_add_tool(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool: memory.event.add
    Args:
      - event_type: str (required)
      - actor: str (default: "Samson")
      - details: dict (default: {})
    """
    hub = _get_memory_hub(deps)
    if hub is None:
        return {"ok": False, "error": {"code": "NO_MEMORY_HUB", "message": "MemoryHub not available."}}

    event_type = args.get("event_type")
    if not isinstance(event_type, str) or not event_type.strip():
        return {"ok": False, "error": {"code": "BAD_REQUEST", "message": "event_type is required"}}

    actor = args.get("actor", "Samson")
    if not isinstance(actor, str) or not actor.strip():
        actor = "Samson"

    details = args.get("details", {})
    if not isinstance(details, dict):
        details = {"value": str(details)}

    # hard bound details size (avoid dumping massive payloads)
    if len(details.keys()) > 30:
        keys = sorted(details.keys(), key=lambda x: str(x))[:30]
        details = {k: details.get(k) for k in keys}
        details["…"] = True

    fn = getattr(hub, "log_event", None)
    if not callable(fn):
        # try episodic store directly if present
        epi = getattr(hub, "episodic", None)
        fn2 = getattr(epi, "add_event", None) or getattr(epi, "record_event", None) or getattr(epi, "log_event", None)
        if callable(fn2):
            fn2(event_type, actor, details)
            return {"ok": True, "status": "logged", "event_type": event_type, "actor": actor}
        return {"ok": False, "error": {"code": "EPISODIC_API_MISSING", "message": "No log_event/add_event method found."}}

    fn(event_type, actor, details)
    return {"ok": True, "status": "logged", "event_type": event_type, "actor": actor}


def memory_event_recent_tool(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool: memory.event.recent
    Args:
      - limit: int (default 10, bounded 1..50)
    """
    hub = _get_memory_hub(deps)
    if hub is None:
        return {"ok": False, "error": {"code": "NO_MEMORY_HUB", "message": "MemoryHub not available."}}

    limit = int(args.get("limit", 10) or 10)
    limit = max(1, min(limit, 50))

    fn = getattr(hub, "recall_recent_events", None)
    if not callable(fn):
        epi = getattr(hub, "episodic", None)
        fn2 = getattr(epi, "get_recent_events", None) or getattr(epi, "recent_events", None)
        if callable(fn2):
            evs = fn2(limit)
        else:
            return {"ok": False, "error": {"code": "EPISODIC_API_MISSING", "message": "No recent events method found."}}
    else:
        evs = fn(limit)

    evs = evs if isinstance(evs, list) else []
    # hard bound + stable type
    evs = evs[:limit]

    return {"ok": True, "returned": len(evs), "events": evs}


def memory_event_search_tool(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tool: memory.event.search
    Args:
      - query: str (required)
      - limit: int (default 10, bounded 1..50)
    """
    hub = _get_memory_hub(deps)
    if hub is None:
        return {"ok": False, "error": {"code": "NO_MEMORY_HUB", "message": "MemoryHub not available."}}

    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"ok": False, "error": {"code": "BAD_REQUEST", "message": "query is required"}}
    query = query.strip()

    limit = int(args.get("limit", 10) or 10)
    limit = max(1, min(limit, 50))

    fn = getattr(hub, "search_events", None)
    if not callable(fn):
        epi = getattr(hub, "episodic", None)
        fn2 = getattr(epi, "search_events", None) or getattr(epi, "find_events", None)
        if callable(fn2):
            evs = fn2(query)
        else:
            return {"ok": False, "error": {"code": "EPISODIC_API_MISSING", "message": "No search method found."}}
    else:
        evs = fn(query)

    evs = evs if isinstance(evs, list) else []
    evs = evs[:limit]

    return {"ok": True, "query": query, "returned": len(evs), "events": evs}
