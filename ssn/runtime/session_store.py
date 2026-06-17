# ssn/runtime/session_store.py
"""
File-backed HTTP session store for Front Door conversations.
"""

from __future__ import annotations

import json
import os
import time
import uuid
from typing import Any, Dict, Optional

from ssn.runtime.frontdoor_context import normalize_session_id, _UNSAFE_FILENAME_RE


def _default_state_dir() -> str:
    return os.getenv("SSN_STATE_DIR") or ".ssn_state"


class SessionStore:
    """
    Persists session metadata under ${SSN_STATE_DIR}/sessions/{session_id}.json
    """

    def __init__(self, base_dir: Optional[str] = None) -> None:
        root = base_dir or os.path.join(_default_state_dir(), "sessions")
        self.base_dir = root
        os.makedirs(self.base_dir, exist_ok=True)

    def _path(self, session_id: str) -> str:
        sid = normalize_session_id(session_id)
        safe = _UNSAFE_FILENAME_RE.sub("_", sid)
        return os.path.join(self.base_dir, f"{safe}.json")

    def _read(self, session_id: str) -> Dict[str, Any]:
        path = self._path(session_id)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    def _write(self, session_id: str, data: Dict[str, Any]) -> None:
        path = self._path(session_id)
        tmp = f"{path}.tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

    def get_or_create(self, session_id: Optional[str] = None) -> Dict[str, Any]:
        sid = normalize_session_id(session_id)
        now = time.time()
        rec = self._read(sid)
        if not rec:
            rec = {
                "session_id": sid,
                "turn_id": 0,
                "created_at": now,
                "updated_at": now,
                "last_session_state": {},
            }
            self._write(sid, rec)
        return rec

    def bump_turn(self, session_id: str) -> int:
        rec = self.get_or_create(session_id)
        turn = int(rec.get("turn_id") or 0) + 1
        rec["turn_id"] = turn
        rec["updated_at"] = time.time()
        self._write(rec["session_id"], rec)
        return turn

    def save_session_state(self, session_id: str, session_state: Optional[dict]) -> None:
        if not isinstance(session_state, dict):
            return
        rec = self.get_or_create(session_id)
        rec["last_session_state"] = session_state
        rec["updated_at"] = time.time()
        self._write(rec["session_id"], rec)

    def new_session_id(self) -> str:
        return f"http-{uuid.uuid4().hex}"
