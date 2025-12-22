# ssn/tools/memory_pending_tools.py

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from ssn.tools.contracts import ToolSpec
from ssn.memory import proposal_store


def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        v = value.strip().lower()
        if v in ("1", "true", "yes", "y", "on"):
            return True
        if v in ("0", "false", "no", "n", "off"):
            return False
    return default


def _truncate_str(v: Any, n: int) -> str:
    if not isinstance(v, str):
        return ""
    return v.strip()[: max(0, n)]


def _safe_created_at(rec: Dict[str, Any]) -> float:
    try:
        return float(rec.get("created_at") or 0.0)
    except Exception:
        return 0.0


def _preview_facts(facts: Any, preview_n: int) -> List[Dict[str, Any]]:
    if not isinstance(facts, list) or not facts or preview_n <= 0:
        return []
    out: List[Dict[str, Any]] = []
    for f in facts[:preview_n]:
        if not isinstance(f, dict):
            continue
        out.append(
            {
                "key": _truncate_str(f.get("key"), 200),
                "value": _truncate_str(f.get("value"), 240),
                "source_url": _truncate_str(f.get("source_url"), 1000) if isinstance(f.get("source_url"), str) else "",
                "source_title": _truncate_str(f.get("source_title"), 300) if isinstance(f.get("source_title"), str) else "",
                "confidence": f.get("confidence") if isinstance(f.get("confidence"), (int, float)) else None,
            }
        )
    return out


def memory_pending_list_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    List pending proposals from canonical disk store (read-only).
    """
    limit = max(1, min(_safe_int(args.get("limit"), 20), 200))

    include_facts_preview = _safe_bool(args.get("include_facts_preview"), default=True)
    preview_n = max(0, min(_safe_int(args.get("preview_n"), 3), 10))
    include_source = _safe_bool(args.get("include_source"), default=True)

    status_filter: Optional[str] = None
    sf = args.get("status")
    if isinstance(sf, str) and sf.strip():
        v = sf.strip().upper()
        if v in ("PENDING", "REJECTED", "COMMITTED", "EXPIRED"):
            status_filter = v

    pending = proposal_store.load_pending()
    if not isinstance(pending, dict):
        pending = {}

    items: List[Dict[str, Any]] = []
    for pid, rec in pending.items():
        if not isinstance(pid, str) or not isinstance(rec, dict):
            continue

        status = rec.get("status")
        status_norm = status.strip().upper() if isinstance(status, str) and status.strip() else "PENDING"
        if status_filter and status_norm != status_filter:
            continue

        facts = rec.get("facts")
        fact_count = len(facts) if isinstance(facts, list) else 0

        created_at_f = _safe_created_at(rec)

        obj: Dict[str, Any] = {
            "proposal_id": pid,
            "status": status_norm,
            "created_at": rec.get("created_at"),
            "_created_at_sort": created_at_f,  # internal sort key
            "summary": _truncate_str(rec.get("summary"), 600),
            "origin": _truncate_str(rec.get("origin"), 160),
            "fact_count": fact_count,
        }

        if include_source:
            src = rec.get("source")
            obj["source"] = src if isinstance(src, dict) else {}

        if include_facts_preview:
            obj["facts_preview"] = _preview_facts(facts, preview_n=preview_n)

        items.append(obj)

    # newest first
    items.sort(key=lambda x: float(x.get("_created_at_sort") or 0.0), reverse=True)
    items = items[:limit]

    # remove internal key before returning
    for it in items:
        it.pop("_created_at_sort", None)

    return {
        "count": len(items),
        "limit": limit,
        "items": items,
        "state_dir": proposal_store.get_state_dir(),
        "listed_at": time.time(),
        "note": "memory.pending.list (disk canonical; read-only)",
    }


def memory_pending_get_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Fetch a single proposal by id from pending OR history (read-only).
    """
    pid = args.get("proposal_id")
    if not isinstance(pid, str) or not pid.strip():
        return {"error": {"code": "INVALID_PROPOSAL_ID", "message": "Missing or invalid 'proposal_id'"}}
    pid = pid.strip()

    rec, location = proposal_store.get_from_pending_or_history(pid)
    if not isinstance(rec, dict):
        return {"error": {"code": "PROPOSAL_NOT_FOUND", "message": "Unknown proposal_id"}}

    max_facts = max(0, min(_safe_int(args.get("max_facts"), 50), 200))

    out = dict(rec)
    if isinstance(out.get("facts"), list):
        out["facts"] = out["facts"][:max_facts]

    return {
        "proposal_id": pid,
        "location": location,  # "pending" | "history"
        "record": out,
        "state_dir": proposal_store.get_state_dir(),
        "fetched_at": time.time(),
        "note": "memory.pending.get (read-only; disk canonical)",
    }


MEMORY_PENDING_LIST_T = ToolSpec(
    name="memory.pending.list",
    description="List pending memory proposals (disk canonical; read-only; OWNER-only).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=False,
    external_effect=False,
    public=False,
    max_calls_per_minute=60,
    input_schema={
        "limit": {"type": "integer", "required": False, "description": "Max proposals to return (1–200)"},
        "status": {"type": "string", "required": False, "description": "Optional filter: PENDING/COMMITTED/REJECTED/EXPIRED"},
        "include_facts_preview": {"type": "boolean", "required": False, "description": "Include facts_preview"},
        "preview_n": {"type": "integer", "required": False, "description": "Facts preview count (0–10)"},
        "include_source": {"type": "boolean", "required": False, "description": "Include source/provenance object"},
    },
    handler=memory_pending_list_handler,
)

MEMORY_PENDING_GET_T = ToolSpec(
    name="memory.pending.get",
    description="Get one proposal from pending/history (read-only; OWNER-only).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=False,
    external_effect=False,
    public=False,
    max_calls_per_minute=120,
    input_schema={
        "proposal_id": {"type": "string", "required": True, "description": "Proposal id"},
        "max_facts": {"type": "integer", "required": False, "description": "Max facts to return (0–200)"},
    },
    handler=memory_pending_get_handler,
)


def register_memory_pending_tools(registry: Any) -> None:
    registry.register(MEMORY_PENDING_LIST_T)
    registry.register(MEMORY_PENDING_GET_T)
