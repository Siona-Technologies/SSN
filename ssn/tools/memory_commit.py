# ssn/tools/memory_commit.py

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

from ssn.tools.contracts import ToolSpec


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


def _get_pending_store(memory: Any) -> Dict[str, Any]:
    """
    Shared with memory.propose: pending proposals live on the MemoryHub instance
    under memory._pending_memory_proposals (no MemoryHub source modification).
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
    Lightweight audit trail (optional) stored on MemoryHub instance.
    """
    if not hasattr(memory, "_memory_proposal_history"):
        setattr(memory, "_memory_proposal_history", {})
    store = getattr(memory, "_memory_proposal_history")
    if not isinstance(store, dict):
        store = {}
        setattr(memory, "_memory_proposal_history", store)
    return store


def _prune_history(history: Dict[str, Any], *, ttl_s: int, max_items: int) -> None:
    if not isinstance(history, dict) or not history:
        return

    now = time.time()

    # TTL prune
    to_delete: List[str] = []
    for pid, rec in list(history.items()):
        try:
            created = rec.get("created_at")
            created_f = float(created) if isinstance(created, (int, float)) else 0.0
            if created_f <= 0.0 or (now - created_f) > float(ttl_s):
                to_delete.append(pid)
        except Exception:
            to_delete.append(pid)

    for pid in to_delete:
        history.pop(pid, None)

    # Max size prune (keep newest)
    if len(history) <= max_items:
        return

    sortable: List[Tuple[float, str]] = []
    for pid, rec in history.items():
        created = rec.get("created_at")
        created_f = float(created) if isinstance(created, (int, float)) else 0.0
        sortable.append((created_f, pid))

    sortable.sort(reverse=True)
    keep = set(pid for _, pid in sortable[:max_items])
    for pid in list(history.keys()):
        if pid not in keep:
            history.pop(pid, None)


def _apply_fact_to_memory(memory: Any, fact: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Best-effort commit into MemoryHub using whichever semantic-fact API exists.
    We avoid changing MemoryHub by probing for known method names.

    Returns: (ok, method_used)
    """
    key = fact.get("key")
    value = fact.get("value")

    if not isinstance(key, str) or not key.strip():
        return False, "invalid_key"
    if not isinstance(value, str) or not value.strip():
        return False, "invalid_value"

    source_url = fact.get("source_url")
    source_title = fact.get("source_title")
    confidence = fact.get("confidence")

    provenance: Dict[str, Any] = {}
    if isinstance(source_url, str) and source_url.strip():
        provenance["url"] = source_url.strip()
    if isinstance(source_title, str) and source_title.strip():
        provenance["title"] = source_title.strip()
    if isinstance(confidence, (int, float)):
        provenance["confidence"] = max(0.0, min(float(confidence), 1.0))

    # Try common semantic-fact APIs first
    candidates = [
        ("add_fact", (key.strip(), value.strip()), {"source": provenance}),
        ("upsert_fact", (key.strip(), value.strip()), {"source": provenance}),
        ("store_fact", (key.strip(), value.strip()), {"source": provenance}),
        ("remember_fact", (key.strip(), value.strip()), {"source": provenance}),
        ("set_fact", (key.strip(), value.strip()), {}),
        ("add_semantic_fact", (fact,), {}),
    ]

    for name, a, kw in candidates:
        fn = getattr(memory, name, None)
        if callable(fn):
            try:
                try:
                    fn(*a, **{k: v for k, v in kw.items() if v is not None})
                except TypeError:
                    fn(*a)
                return True, name
            except Exception:
                # try next candidate
                pass

    # Final fallback: push into any available indexer (better than losing the commit)
    auto_index = getattr(memory, "auto_index_from_text", None)
    if callable(auto_index):
        try:
            prov = provenance.get("url") or ""
            line = f"FACT: {key.strip()} = {value.strip()}"
            if prov:
                line += f" (source: {prov})"
            auto_index("OWNER", line)
            return True, "auto_index_from_text"
        except Exception:
            pass

    return False, "no_supported_memory_api"


# ---------------------------------------------------------
# Handler
# ---------------------------------------------------------

def memory_commit_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    """
    memory.commit

    - Approve or reject a pending proposal created by memory.propose (often via research.propose).
    - State-changing by design: promotes facts into semantic memory (best-effort).
    - Removes the proposal from pending store to prevent replay, and writes an audit record to history.
    """
    memory = deps.get("memory")
    if memory is None:
        return {"error": {"code": "MISSING_DEPS", "message": "deps['memory'] is required"}}

    role = deps.get("role")
    if not isinstance(role, str) or not role.strip():
        role = "OWNER"

    proposal_id = args.get("proposal_id")
    if not isinstance(proposal_id, str) or not proposal_id.strip():
        return {"error": {"code": "INVALID_PROPOSAL_ID", "message": "Missing or invalid 'proposal_id'"}}
    proposal_id = proposal_id.strip()

    approve = _safe_bool(args.get("approve"), default=False)
    reject = _safe_bool(args.get("reject"), default=False)
    reason = _truncate_str(args.get("reason"), 500)

    if approve and reject:
        return {"error": {"code": "INVALID_ACTION", "message": "Provide only one of approve=True or reject=True"}}

    if not approve and not reject:
        return {
            "error": {
                "code": "NOT_APPROVED",
                "message": "Commit requires explicit approve=True (or reject=True).",
            }
        }

    # Expiry policy
    ttl_s = _safe_int(args.get("ttl_s"), 7 * 24 * 3600)  # default 7 days
    ttl_s = max(3600, min(ttl_s, 30 * 24 * 3600))        # 1 hour .. 30 days

    # History retention policy (independent of pending TTL)
    history_ttl_s = _safe_int(args.get("history_ttl_s"), 30 * 24 * 3600)  # 30 days
    history_ttl_s = max(24 * 3600, min(history_ttl_s, 365 * 24 * 3600))   # 1 day .. 1 year

    history_max_items = _safe_int(args.get("history_max_items"), 2000)
    history_max_items = max(100, min(history_max_items, 50_000))

    store = _get_pending_store(memory)
    record = store.get(proposal_id)
    if not isinstance(record, dict):
        return {"error": {"code": "PROPOSAL_NOT_FOUND", "message": "Unknown proposal_id"}}

    status = record.get("status") if isinstance(record.get("status"), str) else "PENDING"
    now = time.time()

    created_at = _safe_float(record.get("created_at"), 0.0)
    if created_at > 0 and (now - created_at) > float(ttl_s):
        # Expire, archive, remove from pending
        record["status"] = "EXPIRED"
        record["expired_at"] = now

        history = _get_history_store(memory)
        history[proposal_id] = record
        store.pop(proposal_id, None)
        _prune_history(history, ttl_s=history_ttl_s, max_items=history_max_items)

        return {
            "error": {
                "code": "PROPOSAL_EXPIRED",
                "message": f"Proposal expired (age exceeded ttl_s={ttl_s}). Create a new proposal.",
            }
        }

    # Idempotency / state machine
    if status == "COMMITTED":
        return {
            "proposal_id": proposal_id,
            "status": "COMMITTED",
            "committed_at": record.get("committed_at"),
            "committed_count": _safe_int(record.get("committed_count"), 0),
            "failed_count": _safe_int(record.get("failed_count"), 0),
            "note": "memory.commit (idempotent): already committed",
        }

    if status == "REJECTED":
        return {"error": {"code": "PROPOSAL_REJECTED", "message": "Proposal was rejected and cannot be committed."}}

    if status != "PENDING":
        return {"error": {"code": "INVALID_STATUS", "message": f"Proposal is in status '{status}' and cannot be committed."}}

    facts = record.get("facts")
    if not isinstance(facts, list) or not facts:
        return {"error": {"code": "EMPTY_PROPOSAL", "message": "Proposal has no facts"}}

    # Reject flow
    if reject:
        record["status"] = "REJECTED"
        record["rejected_at"] = now
        if reason:
            record["reason"] = reason

        history = _get_history_store(memory)
        history[proposal_id] = record
        store.pop(proposal_id, None)
        _prune_history(history, ttl_s=history_ttl_s, max_items=history_max_items)

        return {
            "proposal_id": proposal_id,
            "status": "REJECTED",
            "rejected_at": now,
            "reason": reason,
            "note": "memory.commit (rejected; removed from pending; archived to history)",
        }

    # Commit flow
    committed_at = now
    committed: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    methods_used: List[str] = []

    # Avoid committing duplicate keys in one proposal
    seen_keys = set()

    for f in facts:
        if not isinstance(f, dict):
            continue

        k = f.get("key")
        ks = k.strip() if isinstance(k, str) else ""
        if ks:
            if ks in seen_keys:
                continue
            seen_keys.add(ks)

        ok, method = _apply_fact_to_memory(memory, f)
        methods_used.append(method)

        if ok:
            committed.append({"key": ks or f.get("key"), "method": method})
        else:
            failed.append({"key": ks or f.get("key"), "method": method})

    record["status"] = "COMMITTED"
    record["committed_at"] = committed_at
    record["committed_count"] = len(committed)
    record["failed_count"] = len(failed)
    record["methods_used"] = list(dict.fromkeys(methods_used))[:20]
    record["committed_preview"] = committed[:10]
    record["failed_preview"] = failed[:10]

    history = _get_history_store(memory)
    history[proposal_id] = record
    store.pop(proposal_id, None)
    _prune_history(history, ttl_s=history_ttl_s, max_items=history_max_items)

    return {
        "proposal_id": proposal_id,
        "status": "COMMITTED",
        "committed_at": committed_at,
        "committed_count": len(committed),
        "failed_count": len(failed),
        "committed": committed[:10],
        "failed": failed[:10],
        "methods_used": record["methods_used"],
        "note": "memory.commit (state-changing; approval-gated; archived to history)",
    }


# ---------------------------------------------------------
# ToolSpec
# ---------------------------------------------------------

MEMORY_COMMIT_T = ToolSpec(
    name="memory.commit",
    description="Commit or reject a proposed memory update (state-changing; requires approve=True or reject=True).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=True,
    external_effect=False,
    public=False,
    max_calls_per_minute=30,
    input_schema={
        "proposal_id": {"type": "string", "required": True, "description": "Proposal id returned by memory.propose"},
        "approve": {"type": "boolean", "required": False, "description": "Set True to commit"},
        "reject": {"type": "boolean", "required": False, "description": "Set True to reject instead of commit"},
        "reason": {"type": "string", "required": False, "description": "Reason for rejection (optional)"},
        "ttl_s": {"type": "integer", "required": False, "description": "Pending expiry (1 hour .. 30 days). Default 7 days."},
        "history_ttl_s": {"type": "integer", "required": False, "description": "History retention (1 day .. 1 year). Default 30 days."},
        "history_max_items": {"type": "integer", "required": False, "description": "Max history items to keep (100..50000). Default 2000."},
    },
    handler=memory_commit_handler,
)
