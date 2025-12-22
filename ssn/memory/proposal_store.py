# ssn/memory/proposal_store.py

"""
Persistent proposal store for Phase 7.2+ memory approval workflow.

Why this exists:
- memory.propose creates a PENDING proposal.
- memory.commit is typically executed later (often in a new Python process).
- In-memory storage breaks that workflow (proposal_id "not found").
- This store persists proposals + history to disk safely.

Design goals:
- Dependency-free
- Atomic writes (os.replace)
- Best-effort lock (lockfile with O_EXCL) + stale lock recovery
- Bounded growth: TTL prune + max_items prune
- Owner-safe: stores only bounded proposal payloads (callers enforce bounds)
"""

from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, Optional, Tuple

# Filenames inside state dir
_PENDING_FILE = "pending_memory_proposals.json"
_HISTORY_FILE = "memory_proposal_history.json"
_LOCK_FILE = ".proposal_store.lock"

# Lock behavior (bounded)
_LOCK_TIMEOUT_S_DEFAULT = 1.5
_LOCK_STALE_S_DEFAULT = 30.0  # if lock older than this, treat as stale and recover


def _now() -> float:
    return time.time()


def _safe_float(v: Any, default: float) -> float:
    try:
        return float(v)
    except Exception:
        return default


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def _find_repo_root(start: Optional[str] = None, max_up: int = 6) -> str:
    """
    Try to find a stable project root for default state storage.
    Looks for common markers. Falls back to cwd.
    """
    cur = os.path.abspath(start or os.getcwd())
    for _ in range(max_up + 1):
        for marker in (".git", "pyproject.toml", "setup.cfg", "requirements.txt"):
            if os.path.exists(os.path.join(cur, marker)):
                return cur
        parent = os.path.dirname(cur)
        if parent == cur:
            break
        cur = parent
    return os.path.abspath(os.getcwd())


def get_state_dir() -> str:
    """
    Resolve state dir:
      1) SSN_STATE_DIR env if set
      2) <repo_root>/.ssn_state
    """
    env = os.getenv("SSN_STATE_DIR")
    if isinstance(env, str) and env.strip():
        p = os.path.abspath(env.strip())
        _ensure_dir(p)
        return p

    root = _find_repo_root()
    p = os.path.join(root, ".ssn_state")
    _ensure_dir(p)
    return p


def get_paths() -> Dict[str, str]:
    """
    Canonical absolute paths for store files.
    Use this in scripts/tools (avoid hardcoding filenames elsewhere).
    """
    state_dir = get_state_dir()
    return {
        "state_dir": state_dir,
        "pending_path": os.path.join(state_dir, _PENDING_FILE),
        "history_path": os.path.join(state_dir, _HISTORY_FILE),
        "lock_path": os.path.join(state_dir, _LOCK_FILE),
    }


def _lock_path(state_dir: str) -> str:
    return os.path.join(state_dir, _LOCK_FILE)


def _pid_is_alive(pid: int) -> bool:
    """
    Best-effort liveness check.
    - On Unix: os.kill(pid, 0)
    - On Windows: may raise; treat as unknown (return True to avoid unsafe deletion).
    """
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except PermissionError:
        # Process exists but we may not have permission -> treat as alive.
        return True
    except Exception:
        return False


def _try_clear_stale_lock(state_dir: str, *, stale_after_s: float) -> bool:
    """
    If the lock file looks stale (old and/or pid not alive), remove it.
    Returns True if removed.
    """
    path = _lock_path(state_dir)
    try:
        st = os.stat(path)
    except FileNotFoundError:
        return False
    except Exception:
        return False

    age = _now() - float(getattr(st, "st_mtime", _now()))
    if age < max(1.0, float(stale_after_s)):
        return False

    # Try to read pid to make a safer decision
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            raw = (f.read() or "").strip()
        pid = int(raw) if raw.isdigit() else 0
    except Exception:
        pid = 0

    # If pid is clearly dead (or unknown), we can clear.
    if pid and _pid_is_alive(pid):
        return False

    try:
        os.remove(path)
        return True
    except Exception:
        return False


def _acquire_lock(
    state_dir: str,
    timeout_s: float = _LOCK_TIMEOUT_S_DEFAULT,
    stale_after_s: float = _LOCK_STALE_S_DEFAULT,
) -> Optional[int]:
    """
    Best-effort lock via exclusive creation. Returns fd if acquired.

    If it cannot be acquired quickly, returns None (atomic writes still prevent partial files).

    Includes stale-lock recovery (bounded) to avoid deadlocks after crashes.
    """
    _ensure_dir(state_dir)

    path = _lock_path(state_dir)
    deadline = _now() + max(0.2, float(timeout_s))
    while _now() < deadline:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            try:
                os.write(fd, str(os.getpid()).encode("utf-8", errors="replace"))
            except Exception:
                pass
            return fd
        except FileExistsError:
            # Attempt stale-lock recovery (bounded + safe)
            _try_clear_stale_lock(state_dir, stale_after_s=stale_after_s)
            time.sleep(0.05)
        except Exception:
            return None
    return None


def _release_lock(state_dir: str, fd: Optional[int]) -> None:
    try:
        if fd is not None:
            try:
                os.close(fd)
            except Exception:
                pass
        try:
            os.remove(_lock_path(state_dir))
        except Exception:
            pass
    except Exception:
        pass


def _read_json(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            obj = json.load(f)
        return obj if isinstance(obj, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception:
        # Corrupted or partial file (should be rare due to atomic writes).
        # Fail closed by returning empty.
        return {}


def _atomic_write_json(path: str, obj: Dict[str, Any]) -> None:
    """
    Atomic write: write temp file, fsync, then os.replace.
    """
    parent = os.path.dirname(os.path.abspath(path))
    _ensure_dir(parent)

    tmp = f"{path}.tmp"
    data = json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)

    with open(tmp, "w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        try:
            os.fsync(f.fileno())
        except Exception:
            pass

    # Best-effort tighten permissions on unix-like systems
    try:
        os.chmod(tmp, 0o600)
    except Exception:
        pass

    os.replace(tmp, path)

    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def _prune_records(records: Dict[str, Any], *, ttl_s: int, max_items: int) -> Dict[str, Any]:
    """
    records: {proposal_id: record}
    Keeps newest by created_at. Removes items older than ttl_s.
    """
    if not isinstance(records, dict) or not records:
        return {}

    now = _now()
    ttl = max(3600, int(ttl_s))  # clamp to >= 1 hour
    mx = max(10, int(max_items))

    # 1) TTL prune
    kept: Dict[str, Any] = {}
    for pid, rec in records.items():
        if not isinstance(pid, str) or not isinstance(rec, dict):
            continue
        created = _safe_float(rec.get("created_at"), 0.0)
        if created <= 0.0:
            continue
        if (now - created) <= float(ttl):
            kept[pid] = rec

    if len(kept) <= mx:
        return kept

    # 2) Size prune: keep newest
    sortable: list[Tuple[float, str]] = []
    for pid, rec in kept.items():
        sortable.append((_safe_float(rec.get("created_at"), 0.0), pid))
    sortable.sort(reverse=True)

    keep_ids = set(pid for _, pid in sortable[:mx])
    return {pid: kept[pid] for pid in keep_ids if pid in kept}


def _paths() -> Tuple[str, str, str]:
    p = get_paths()
    return p["state_dir"], p["pending_path"], p["history_path"]


def load_pending() -> Dict[str, Any]:
    _, pending_path, _ = _paths()
    return _read_json(pending_path)


def save_pending(store: Dict[str, Any]) -> None:
    state_dir, pending_path, _ = _paths()
    fd = _acquire_lock(state_dir)
    try:
        _atomic_write_json(pending_path, store if isinstance(store, dict) else {})
    finally:
        _release_lock(state_dir, fd)


def load_history() -> Dict[str, Any]:
    _, _, history_path = _paths()
    return _read_json(history_path)


def save_history(store: Dict[str, Any]) -> None:
    state_dir, _, history_path = _paths()
    fd = _acquire_lock(state_dir)
    try:
        _atomic_write_json(history_path, store if isinstance(store, dict) else {})
    finally:
        _release_lock(state_dir, fd)


def upsert_pending(
    proposal_id: str,
    record: Dict[str, Any],
    *,
    ttl_s: int,
    max_pending: int,
) -> None:
    """
    Insert/update pending record, prune, then persist.
    """
    if not isinstance(proposal_id, str) or not proposal_id.strip():
        return
    if not isinstance(record, dict):
        return

    store = load_pending()
    store[proposal_id.strip()] = record
    store = _prune_records(store, ttl_s=ttl_s, max_items=max_pending)
    save_pending(store)


def move_pending_to_history(
    proposal_id: str,
    record: Dict[str, Any],
    *,
    history_ttl_s: int = 30 * 24 * 3600,
    max_history: int = 2000,
) -> None:
    """
    Persist record to history (bounded), and remove from pending if present.
    """
    pid = proposal_id.strip() if isinstance(proposal_id, str) else ""
    if not pid:
        return

    pending = load_pending()
    if isinstance(pending, dict) and pid in pending:
        pending.pop(pid, None)
        # Keep pending store generous; callers (memory.propose) also prune.
        save_pending(_prune_records(pending, ttl_s=7 * 24 * 3600, max_items=5000))

    history = load_history()
    history[pid] = record if isinstance(record, dict) else {}
    history = _prune_records(history, ttl_s=history_ttl_s, max_items=max_history)
    save_history(history)


def get_from_pending_or_history(proposal_id: str) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Returns (record, location) where location ∈ {"pending","history","missing"}.
    """
    pid = proposal_id.strip() if isinstance(proposal_id, str) else ""
    if not pid:
        return None, "missing"

    pending = load_pending()
    rec = pending.get(pid) if isinstance(pending, dict) else None
    if isinstance(rec, dict):
        return rec, "pending"

    history = load_history()
    rec2 = history.get(pid) if isinstance(history, dict) else None
    if isinstance(rec2, dict):
        return rec2, "history"

    return None, "missing"
