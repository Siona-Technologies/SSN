# ssn/tools/memory_propose.py

from __future__ import annotations

import secrets
import time
from typing import Any, Dict, List, Optional, Tuple

from ssn.tools.contracts import ToolSpec

# Canonical persistent store (disk is source of truth)
from ssn.memory import proposal_store


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _safe_float(value: Any, default: float) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _truncate_str(v: Any, n: int) -> str:
    if not isinstance(v, str):
        return ""
    return v.strip()[: max(0, n)]


def _get_pending_store(memory: Any) -> Dict[str, Any]:
    """
    In-memory store on MemoryHub instance (fast path cache).
    Disk is canonical; memory is a cache.
    """
    if not hasattr(memory, "_pending_memory_proposals"):
        setattr(memory, "_pending_memory_proposals", {})
    store = getattr(memory, "_pending_memory_proposals")
    if not isinstance(store, dict):
        store = {}
        setattr(memory, "_pending_memory_proposals", store)
    return store


def _get_history_store(memory: Any) -> Dict[str, Any]:
    """
    Optional in-memory audit store (cache).
    """
    if not hasattr(memory, "_memory_proposal_history"):
        setattr(memory, "_memory_proposal_history", {})
    store = getattr(memory, "_memory_proposal_history")
    if not isinstance(store, dict):
        store = {}
        setattr(memory, "_memory_proposal_history", store)
    return store


def _prune_store(store: Dict[str, Any], *, ttl_s: int, max_items: int) -> None:
    """
    Prevent unbounded growth in the in-memory cache.
    Disk pruning is handled by proposal_store, but we keep cache tidy too.
    """
    if not isinstance(store, dict) or not store:
        return

    now = time.time()

    # TTL prune
    to_delete: List[str] = []
    for pid, rec in list(store.items()):
        try:
            created = rec.get("created_at")
            created_f = float(created) if isinstance(created, (int, float)) else 0.0
            if created_f <= 0.0 or (now - created_f) > float(ttl_s):
                to_delete.append(pid)
        except Exception:
            to_delete.append(pid)

    for pid in to_delete:
        store.pop(pid, None)

    # Size prune (keep newest)
    if len(store) <= max_items:
        return

    sortable: List[Tuple[float, str]] = []
    for pid, rec in store.items():
        created = rec.get("created_at")
        created_f = float(created) if isinstance(created, (int, float)) else 0.0
        sortable.append((created_f, pid))

    sortable.sort(reverse=True)
    keep = set(pid for _, pid in sortable[:max_items])
    for pid in list(store.keys()):
        if pid not in keep:
            store.pop(pid, None)


def _sanitize_fact_item(item: Any) -> Dict[str, Any]:
    """
    Expected minimal structure:
      {"key": str, "value": str, optional: "source_url", "source_title", "confidence", "note"}
    """
    if not isinstance(item, dict):
        return {}

    key = item.get("key")
    value = item.get("value")

    if not isinstance(key, str) or not key.strip():
        return {}
    if not isinstance(value, str) or not value.strip():
        return {}

    out: Dict[str, Any] = {
        "key": key.strip()[:200],
        "value": value.strip()[:2000],
    }

    source_url = item.get("source_url")
    if isinstance(source_url, str) and source_url.strip():
        out["source_url"] = source_url.strip()[:1000]

    source_title = item.get("source_title")
    if isinstance(source_title, str) and source_title.strip():
        out["source_title"] = source_title.strip()[:300]

    confidence = item.get("confidence")
    if isinstance(confidence, (int, float)):
        out["confidence"] = max(0.0, min(float(confidence), 1.0))

    note = item.get("note")
    if isinstance(note, str) and note.strip():
        out["note"] = note.strip()[:500]

    return out


def _pick_facts_list(args: Dict[str, Any]) -> Optional[List[Any]]:
    """
    Be tolerant: research.propose may send facts under various keys.
    We take the first non-empty list in priority order.
    """
    for k in ("facts", "items", "entries", "proposals", "candidate_facts"):
        v = args.get(k)
        if isinstance(v, list) and v:
            return v
    return None


def _pick_text_facts(args: Dict[str, Any]) -> Optional[List[str]]:
    for k in ("facts_text", "raw_facts"):
        v = args.get(k)
        if isinstance(v, list) and v:
            out: List[str] = []
            for item in v:
                if isinstance(item, str) and item.strip():
                    out.append(item.strip())
            return out if out else None
    return None


def _coerce_text_facts_to_kv(text_facts: List[str], *, max_facts: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for i, t in enumerate(text_facts[:max_facts]):
        out.append({"key": f"fact_{i+1}", "value": t[:2000]})
    return out


def _sanitize_source(source: Any) -> Dict[str, Any]:
    """
    Keep provenance bounded. Do not enforce strict schema here.
    """
    if not isinstance(source, dict):
        return {}
    out: Dict[str, Any] = {}

    for k, limit in (
        ("type", 50),
        ("query", 500),
        ("url", 1000),
        ("title", 300),
        ("provider", 80),
        ("origin", 120),
    ):
        v = source.get(k)
        if isinstance(v, str) and v.strip():
            out[k] = v.strip()[:limit]

    for k in ("degraded", "offline"):
        v = source.get(k)
        if isinstance(v, bool):
            out[k] = v

    return out


def _hydrate_caches_from_disk(memory: Any, *, ttl_s: int, max_pending: int) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Load pending+history from disk into in-memory caches (disk is canonical).
    Also prune caches.
    """
    pending_disk = proposal_store.load_pending()
    history_disk = proposal_store.load_history()

    pending_mem = _get_pending_store(memory)
    history_mem = _get_history_store(memory)

    # Disk overwrites memory (source-of-truth for restarts)
    for k, v in (pending_disk or {}).items():
        if isinstance(k, str) and isinstance(v, dict):
            pending_mem[k] = v
    for k, v in (history_disk or {}).items():
        if isinstance(k, str) and isinstance(v, dict):
            history_mem[k] = v

    _prune_store(pending_mem, ttl_s=ttl_s, max_items=max_pending)
    # history cache is bounded separately in commit tool; keep generous here
    _prune_store(history_mem, ttl_s=30 * 24 * 3600, max_items=2000)

    return pending_mem, history_mem


# ---------------------------------------------------------
# Tool handler
# ---------------------------------------------------------

def memory_propose_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    memory = deps.get("memory")
    if memory is None:
        return {"error": {"code": "MISSING_DEPS", "message": "deps['memory'] is required"}}

    max_facts = _safe_int(args.get("max_facts"), 25)
    max_facts = max(1, min(max_facts, 50))

    # retention controls (safe defaults)
    ttl_s = _safe_int(args.get("ttl_s"), 7 * 24 * 3600)  # 7 days
    ttl_s = max(3600, min(ttl_s, 30 * 24 * 3600))       # 1 hour .. 30 days

    max_pending = _safe_int(args.get("max_pending"), 200)
    max_pending = max(10, min(max_pending, 2000))

    # Load persisted stores into cache first (ensures cross-process approvals work)
    pending_cache, _history_cache = _hydrate_caches_from_disk(memory, ttl_s=ttl_s, max_pending=max_pending)

    summary = _truncate_str(args.get("summary"), 500)
    origin = _truncate_str(args.get("origin"), 120)

    created_at_arg = args.get("created_at")
    created_at = _safe_float(created_at_arg, time.time())
    if created_at <= 0:
        created_at = time.time()
    if created_at > time.time() + 60:
        created_at = time.time()

    source = _sanitize_source(args.get("source"))

    facts_list = _pick_facts_list(args)
    text_facts = _pick_text_facts(args)

    if facts_list is None and text_facts is None:
        return {
            "error": {
                "code": "INVALID_FACTS",
                "message": (
                    "Missing facts. Provide a non-empty list under one of: "
                    "facts/items/entries/proposals/candidate_facts, or text under facts_text/raw_facts."
                ),
            }
        }

    coerced: List[Any] = (
        facts_list
        if facts_list is not None
        else _coerce_text_facts_to_kv(text_facts or [], max_facts=max_facts)
    )

    cleaned: List[Dict[str, Any]] = []
    for item in coerced[:max_facts]:
        c = _sanitize_fact_item(item)
        if c:
            cleaned.append(c)

    if not cleaned:
        return {"error": {"code": "NO_VALID_FACTS", "message": "No valid facts after validation"}}

    proposal_id = f"prop_{int(time.time())}_{secrets.token_hex(6)}"

    record: Dict[str, Any] = {
        "proposal_id": proposal_id,
        "created_at": created_at,
        "status": "PENDING",
        "summary": summary,
        "origin": origin,
        "source": source,
        "facts": cleaned,
    }

    # Update cache
    pending_cache[proposal_id] = record
    _prune_store(pending_cache, ttl_s=ttl_s, max_items=max_pending)

    # Persist via canonical store (atomic + bounded)
    proposal_store.upsert_pending(proposal_id, record, ttl_s=ttl_s, max_pending=max_pending)

    preview_n = min(5, len(cleaned))

    return {
        "proposal_id": proposal_id,
        "status": "PENDING",
        "created_at": created_at,
        "fact_count": len(cleaned),
        "preview": cleaned[:preview_n],
        "summary": summary,
        "source": source,
        "origin": origin,

        # observability (helps ops/CI)
        "ttl_s": int(ttl_s),
        "max_pending": int(max_pending),

        "state_dir": proposal_store.get_state_dir(),
        "note": "memory.propose (pending proposal persisted; requires explicit memory.commit approval)",
    }


# ---------------------------------------------------------
# ToolSpec
# ---------------------------------------------------------

MEMORY_PROPOSE_T = ToolSpec(
    name="memory.propose",
    description="Propose memory facts for approval (PENDING proposal persisted; requires explicit memory.commit).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    # This tool writes persisted pending proposals (proposal_store) => mark correctly.
    state_changing=True,
    external_effect=True,
    public=False,
    max_calls_per_minute=60,
    input_schema={
        # main input
        "facts": {
            "type": "array",
            "required": False,
            "description": "List of fact objects: {key, value, optional source_url/source_title/confidence/note}",
        },
        # aliases (schema-tolerant)
        "items": {"type": "array", "required": False, "description": "Alias for facts"},
        "entries": {"type": "array", "required": False, "description": "Alias for facts"},
        "proposals": {"type": "array", "required": False, "description": "Alias for facts"},
        "candidate_facts": {"type": "array", "required": False, "description": "Alias for facts"},
        # text-only fallback
        "facts_text": {"type": "array", "required": False, "description": "List of strings (coerced into key/value facts)"},
        "raw_facts": {"type": "array", "required": False, "description": "Alias for facts_text"},
        # metadata
        "summary": {"type": "string", "required": False, "description": "Short summary of proposal"},
        "source": {"type": "object", "required": False, "description": "Provenance (type/query/url/title/provider/degraded/offline)"},
        "origin": {"type": "string", "required": False, "description": "Caller id (e.g., research.propose)"},
        "created_at": {"type": "number", "required": False, "description": "Creation time (epoch seconds)"},
        # bounds
        "max_facts": {"type": "integer", "required": False, "description": "Max facts to accept (1–50)"},
        "ttl_s": {"type": "integer", "required": False, "description": "TTL for pending proposals (seconds)"},
        "max_pending": {"type": "integer", "required": False, "description": "Max pending proposals to keep"},
    },
    handler=memory_propose_handler,
)
