# ssn/tools/memory_commit.py

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

from ssn.tools.contracts import ToolSpec

# Canonical persistent store (shared by memory.propose)
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
    if not hasattr(memory, "_pending_memory_proposals"):
        setattr(memory, "_pending_memory_proposals", {})
    store = getattr(memory, "_pending_memory_proposals")
    if not isinstance(store, dict):
        store = {}
        setattr(memory, "_pending_memory_proposals", store)
    return store


def _get_history_store(memory: Any) -> Dict[str, Any]:
    if not hasattr(memory, "_memory_proposal_history"):
        setattr(memory, "_memory_proposal_history", {})
    store = getattr(memory, "_memory_proposal_history")
    if not isinstance(store, dict):
        store = {}
        setattr(memory, "_memory_proposal_history", store)
    return store


def _state_dir() -> str:
    # Prefer proposal_store canonical resolution
    try:
        paths = getattr(proposal_store, "get_paths", None)
        if callable(paths):
            p = paths()
            if isinstance(p, dict) and isinstance(p.get("state_dir"), str):
                return str(p["state_dir"])
    except Exception:
        pass

    try:
        return str(proposal_store.get_state_dir())
    except Exception:
        # ultra fallback
        env = os.getenv("SSN_STATE_DIR")
        if env and env.strip():
            return env.strip()
        return os.path.join(os.path.expanduser("~"), ".ssn", "state")


def _apply_fact_to_memory(memory: Any, fact: Dict[str, Any], role: str) -> Tuple[bool, str]:
    """
    Try multiple MemoryHub APIs to write a fact.
    Keep robust and non-failing (commit should not crash).
    """
    key = fact.get("key")
    value = fact.get("value")

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

    candidates = [
        ("add_fact", (key, value), {"source": provenance}),
        ("upsert_fact", (key, value), {"source": provenance}),
        ("store_fact", (key, value), {"source": provenance}),
        ("remember_fact", (key, value), {"source": provenance}),
        ("set_fact", (key, value), {}),
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
                pass

    auto_index = getattr(memory, "auto_index_from_text", None)
    if callable(auto_index) and isinstance(key, str) and isinstance(value, str):
        try:
            prov = provenance.get("url") or ""
            line = f"FACT: {key} = {value}"
            if prov:
                line += f" (source: {prov})"
            auto_index(role, line)
            return True, "auto_index_from_text"
        except Exception:
            pass

    return False, "no_supported_memory_api"


# ---------------------------------------------------------
# Handler
# ---------------------------------------------------------

def memory_commit_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    memory = deps.get("memory")
    if memory is None:
        return {"error": {"code": "MISSING_DEPS", "message": "deps['memory'] is required"}}

    role = deps.get("role")
    if not isinstance(role, str):
        role = "OWNER"

    proposal_id = args.get("proposal_id")
    if not isinstance(proposal_id, str) or not proposal_id.strip():
        return {"error": {"code": "INVALID_PROPOSAL_ID", "message": "Missing or invalid 'proposal_id'"}}
    proposal_id = proposal_id.strip()

    approve = _safe_bool(args.get("approve"), default=False)
    reject = _safe_bool(args.get("reject"), default=False)
    reason = _truncate_str(args.get("reason"), 500)

    if reject and approve:
        return {"error": {"code": "INVALID_ACTION", "message": "Provide only one of approve=True or reject=True"}}
    if not approve and not reject:
        return {"error": {"code": "NOT_APPROVED", "message": "Commit requires explicit approve=True (or reject=True)."}}

    # Expiry controls: must match memory.propose defaults (or be compatible)
    ttl_s = _safe_int(args.get("ttl_s"), 7 * 24 * 3600)
    ttl_s = max(3600, min(ttl_s, 30 * 24 * 3600))

    # pending cap used only for store pruning inside propose; kept for API compatibility
    max_pending = _safe_int(args.get("max_pending"), 200)
    max_pending = max(10, min(max_pending, 2000))

    # Canonical lookup (disk is source-of-truth)
    rec, location = proposal_store.get_from_pending_or_history(proposal_id)
    if not isinstance(rec, dict):
        return {"error": {"code": "PROPOSAL_NOT_FOUND", "message": "Unknown proposal_id"}}

    now = time.time()
    status = rec.get("status") if isinstance(rec.get("status"), str) else "PENDING"
    created_at = _safe_float(rec.get("created_at"), 0.0)

    # If record is pending, enforce expiry here
    if location == "pending" and created_at > 0 and (now - created_at) > float(ttl_s):
        rec["status"] = "EXPIRED"
        rec["expired_at"] = now

        # Persist to history and remove from pending
        proposal_store.move_pending_to_history(
            proposal_id,
            rec,
            history_ttl_s=30 * 24 * 3600,
            max_history=2000,
        )

        # Keep in-memory caches aligned (best-effort)
        pending_cache = _get_pending_store(memory)
        history_cache = _get_history_store(memory)
        pending_cache.pop(proposal_id, None)
        history_cache[proposal_id] = rec

        return {
            "error": {"code": "PROPOSAL_EXPIRED", "message": f"Proposal expired (ttl_s={ttl_s}). Create a new one."},
            "proposal_id": proposal_id,
            "state_dir": _state_dir(),
        }

    # Idempotency via history
    if location == "history":
        if status == "COMMITTED":
            return {
                "proposal_id": proposal_id,
                "status": "COMMITTED",
                "committed_at": rec.get("committed_at"),
                "committed_count": _safe_int(rec.get("committed_count"), 0),
                "failed_count": _safe_int(rec.get("failed_count"), 0),
                "methods_used": rec.get("methods_used") or [],
                "state_dir": _state_dir(),
                "note": "memory.commit (idempotent via history): already committed",
            }
        if status == "REJECTED":
            return {
                "proposal_id": proposal_id,
                "status": "REJECTED",
                "rejected_at": rec.get("rejected_at"),
                "reason": rec.get("reason", ""),
                "state_dir": _state_dir(),
                "note": "memory.commit (history): proposal was rejected",
            }
        if status == "EXPIRED":
            return {"error": {"code": "PROPOSAL_EXPIRED", "message": "Proposal is expired (per history). Create a new proposal."}}

        # Unknown history status: treat as non-committable
        return {"error": {"code": "INVALID_STATUS", "message": f"Proposal status '{status}' cannot be committed."}}

    # From here: location == "pending"
    if status == "COMMITTED":
        # Shouldn't happen in pending, but keep safe/idempotent
        return {
            "proposal_id": proposal_id,
            "status": "COMMITTED",
            "committed_at": rec.get("committed_at"),
            "committed_count": _safe_int(rec.get("committed_count"), 0),
            "failed_count": _safe_int(rec.get("failed_count"), 0),
            "methods_used": rec.get("methods_used") or [],
            "state_dir": _state_dir(),
            "note": "memory.commit (idempotent): proposal already committed",
        }

    if status == "REJECTED":
        return {"error": {"code": "PROPOSAL_REJECTED", "message": "Proposal was rejected and cannot be committed."}}

    if status != "PENDING":
        return {"error": {"code": "INVALID_STATUS", "message": f"Proposal status '{status}' cannot be committed."}}

    facts = rec.get("facts")
    if not isinstance(facts, list) or not facts:
        return {"error": {"code": "EMPTY_PROPOSAL", "message": "Proposal has no facts"}}

    # Reject flow
    if reject:
        rec["status"] = "REJECTED"
        rec["rejected_at"] = now
        if reason:
            rec["reason"] = reason

        proposal_store.move_pending_to_history(
            proposal_id,
            rec,
            history_ttl_s=30 * 24 * 3600,
            max_history=2000,
        )

        pending_cache = _get_pending_store(memory)
        history_cache = _get_history_store(memory)
        pending_cache.pop(proposal_id, None)
        history_cache[proposal_id] = rec

        return {
            "proposal_id": proposal_id,
            "status": "REJECTED",
            "rejected_at": now,
            "reason": reason,
            "state_dir": _state_dir(),
            "note": "memory.commit (rejected; archived to history; persisted)",
        }

    # Commit flow
    committed_at = now
    committed: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    methods_used: List[str] = []
    seen_keys = set()

    for f in facts:
        if not isinstance(f, dict):
            continue
        k = f.get("key")
        if isinstance(k, str):
            ks = k.strip()
            if ks in seen_keys:
                continue
            seen_keys.add(ks)

        ok, method = _apply_fact_to_memory(memory, f, role)
        methods_used.append(method)
        if ok:
            committed.append({"key": f.get("key"), "method": method})
        else:
            failed.append({"key": f.get("key"), "method": method})

    rec["status"] = "COMMITTED"
    rec["committed_at"] = committed_at
    rec["committed_count"] = len(committed)
    rec["failed_count"] = len(failed)
    rec["methods_used"] = list(dict.fromkeys(methods_used))[:20]
    rec["committed_preview"] = committed[:10]
    rec["failed_preview"] = failed[:10]

    proposal_store.move_pending_to_history(
        proposal_id,
        rec,
        history_ttl_s=30 * 24 * 3600,
        max_history=2000,
    )

    pending_cache = _get_pending_store(memory)
    history_cache = _get_history_store(memory)
    pending_cache.pop(proposal_id, None)
    history_cache[proposal_id] = rec

    return {
        "proposal_id": proposal_id,
        "status": "COMMITTED",
        "committed_at": committed_at,
        "committed_count": len(committed),
        "failed_count": len(failed),
        "committed": committed[:10],
        "failed": failed[:10],
        "methods_used": rec["methods_used"],
        "state_dir": _state_dir(),
        "note": "memory.commit (committed; archived to history; persisted)",
    }


# ---------------------------------------------------------
# ToolSpec
# ---------------------------------------------------------

MEMORY_COMMIT_T = ToolSpec(
    name="memory.commit",
    description="Commit or reject a proposed memory update (approval-gated; persistent; idempotent via history).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=True,
    external_effect=False,
    public=False,
    max_calls_per_minute=30,
    input_schema={
        "proposal_id": {"type": "string", "required": True, "description": "Proposal id returned by memory.propose"},
        "approve": {"type": "boolean", "required": False, "description": "Must be True to commit"},
        "reject": {"type": "boolean", "required": False, "description": "Set True to reject"},
        "reason": {"type": "string", "required": False, "description": "Reason for rejection"},
        "ttl_s": {"type": "integer", "required": False, "description": "Expiry window seconds (1h..30d), default 7d"},
        "max_pending": {"type": "integer", "required": False, "description": "Pending cap used by persistence pruning (compat)"},
    },
    handler=memory_commit_handler,
)
