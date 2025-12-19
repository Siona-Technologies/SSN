from __future__ import annotations

from typing import Any, Dict, List, Optional


def _get_memory_hub(deps: Dict[str, Any]):
    hub = deps.get("memory_hub")
    if hub is not None:
        return hub

    orch = deps.get("orchestrator")
    if orch is not None:
        for name in ("memory_hub", "memory"):
            h = getattr(orch, name, None)
            if h is not None:
                return h

    return None


def _extract_payload_type(item: Any) -> str:
    if isinstance(item, dict):
        p = item.get("payload")
        if isinstance(p, dict):
            t = p.get("type")
            if isinstance(t, str) and t.strip():
                return t.strip()
        t2 = item.get("type")
        if isinstance(t2, str) and t2.strip():
            return t2.strip()
    return "unknown"


def _stringify_for_search(item: Any) -> str:
    try:
        return str(item).lower()
    except Exception:
        return ""


def _extract_approval_flags(item: Any) -> Optional[Dict[str, bool]]:
    """
    Safely extract approval metadata if present.
    Returns None if not applicable.
    """
    if not isinstance(item, dict):
        return None

    approved = item.get("approved")
    approval_required = item.get("approval_required")

    if isinstance(approved, bool) or isinstance(approval_required, bool):
        return {
            "approval_required": bool(approval_required),
            "approved": bool(approved),
        }

    return None


def memory_trace_recent_tool(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    hub = _get_memory_hub(deps)
    if hub is None:
        return {"ok": False, "error": {"code": "NO_MEMORY_HUB", "message": "MemoryHub not available."}}

    limit = int(args.get("limit", 50) or 50)
    limit = max(1, min(limit, 200))

    fn = getattr(hub, "get_recent_traces", None)
    if not callable(fn):
        tm = getattr(hub, "trace", None) or getattr(hub, "trace_memory", None)
        fn2 = getattr(tm, "get_recent_traces", None)
        if callable(fn2):
            traces = fn2(limit)
        else:
            return {"ok": False, "error": {"code": "TRACE_API_MISSING", "message": "No get_recent_traces available."}}
    else:
        traces = fn(limit)

    traces = traces if isinstance(traces, list) else []
    traces = traces[:limit]

    type_hist: Dict[str, int] = {}
    approval_hist = {"approval_required": 0, "approved": 0, "blocked": 0}

    for it in traces:
        t = _extract_payload_type(it)
        type_hist[t] = type_hist.get(t, 0) + 1

        flags = _extract_approval_flags(it)
        if flags:
            if flags["approval_required"]:
                approval_hist["approval_required"] += 1
                if flags["approved"]:
                    approval_hist["approved"] += 1
                else:
                    approval_hist["blocked"] += 1

    return {
        "ok": True,
        "returned": len(traces),
        "limit": limit,
        "trace_type_histogram": type_hist,
        "approval_histogram": approval_hist,
        "traces": traces,
    }


def memory_trace_types_tool(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    hub = _get_memory_hub(deps)
    if hub is None:
        return {"ok": False, "error": {"code": "NO_MEMORY_HUB", "message": "MemoryHub not available."}}

    limit = int(args.get("limit", 200) or 200)
    limit = max(1, min(limit, 500))

    fn = getattr(hub, "get_recent_traces", None)
    if callable(fn):
        traces = fn(limit)
    else:
        tm = getattr(hub, "trace", None) or getattr(hub, "trace_memory", None)
        fn2 = getattr(tm, "get_recent_traces", None)
        traces = fn2(limit) if callable(fn2) else []

    traces = traces if isinstance(traces, list) else []

    hist: Dict[str, int] = {}
    for it in traces:
        t = _extract_payload_type(it)
        hist[t] = hist.get(t, 0) + 1

    return {"ok": True, "limit": limit, "trace_type_histogram": hist}


def memory_trace_search_tool(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    hub = _get_memory_hub(deps)
    if hub is None:
        return {"ok": False, "error": {"code": "NO_MEMORY_HUB", "message": "MemoryHub not available."}}

    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        return {"ok": False, "error": {"code": "BAD_REQUEST", "message": "query is required"}}
    q = query.strip().lower()

    limit = int(args.get("limit", 25) or 25)
    limit = max(1, min(limit, 100))

    scan_limit = int(args.get("scan_limit", 200) or 200)
    scan_limit = max(1, min(scan_limit, 500))

    fn = getattr(hub, "get_recent_traces", None)
    if callable(fn):
        traces = fn(scan_limit)
    else:
        tm = getattr(hub, "trace", None) or getattr(hub, "trace_memory", None)
        fn2 = getattr(tm, "get_recent_traces", None)
        traces = fn2(scan_limit) if callable(fn2) else []

    traces = traces if isinstance(traces, list) else []

    hits: List[Any] = []
    for it in traces:
        if q in _stringify_for_search(it):
            hits.append(it)
            if len(hits) >= limit:
                break

    return {
        "ok": True,
        "query": query,
        "scan_limit": scan_limit,
        "returned": len(hits),
        "traces": hits,
    }
