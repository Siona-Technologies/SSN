"""
SSN Trace Memory (Phase 3.5)
+ Phase 6.x Compatibility Update
+ Atomic persistence hardening

Stores cognitive snapshots and internal traces.
Useful for:
- debugging brain decisions
- visualizing cognitive flow
- future meta-reasoning
- perception tick traces (Phase 6.0)

Key upgrades:
- Keeps your JSON persistence model (no redesign)
- Adds bounded retention to prevent unbounded growth
- Adds compatibility methods used by newer modules:
    - add_trace(payload)
    - write_trace(payload)
    - log(payload)
    - get_recent_traces(limit)
- Preserves your existing API:
    - store_cognitive_snapshot(packet)
    - recent(n)
    - all()
- Hardens disk writes using atomic replace to reduce corruption risk
"""

from __future__ import annotations

import json
import os
import tempfile
import time
from typing import Any, Dict, List

DEFAULT_PATH = "ssn/data/trace_memory.json"


class TraceMemory:
    # Hard cap to prevent unbounded disk growth (tune as needed)
    MAX_SNAPSHOTS = 5000

    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        if not os.path.exists(self.path):
            # Create an empty file atomically
            self._atomic_write_json(self.path, [])

        self.snapshots: List[Dict[str, Any]] = []
        self._load()

    # ---------------- internal ----------------

    @staticmethod
    def _atomic_write_json(path: str, data: Any) -> None:
        """
        Write JSON atomically:
          1) write to temp file in same directory
          2) flush + fsync
          3) os.replace(temp, path)
          4) best-effort fsync directory (POSIX)
        """
        dir_name = os.path.dirname(path) or "."
        base_name = os.path.basename(path)

        fd = None
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(prefix=base_name + ".", suffix=".tmp", dir=dir_name)
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_path, path)

            # POSIX directory fsync (best effort)
            try:
                dir_fd = os.open(dir_name, os.O_DIRECTORY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except Exception:
                pass

        finally:
            # If something failed before os.replace, ensure temp is removed
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass

    def _load(self) -> None:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.snapshots = data if isinstance(data, list) else []
        except Exception:
            # If file is corrupted or unreadable, fail safe to empty memory
            self.snapshots = []

    def _save(self) -> None:
        # enforce bounded retention before saving
        if len(self.snapshots) > self.MAX_SNAPSHOTS:
            self.snapshots = self.snapshots[-self.MAX_SNAPSHOTS :]

        self._atomic_write_json(self.path, self.snapshots)

    # ---------------- public api (original) ----------------

    def store_cognitive_snapshot(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        """
        packet should contain:
        - input
        - role
        - brain_mode
        - fusion_score
        - timestamp
        - routed_engine
        - identity_info
        etc.
        """
        entry = {
            "timestamp": time.time(),
            "snapshot": packet if isinstance(packet, dict) else {"value": packet},
        }

        self.snapshots.append(entry)
        self._save()
        return entry

    def recent(self, n: int = 5) -> List[Dict[str, Any]]:
        """Return last n snapshots."""
        try:
            n = int(n)
        except Exception:
            n = 5
        if n <= 0:
            return []
        return self.snapshots[-n:]

    def all(self) -> List[Dict[str, Any]]:
        return self.snapshots

    # ---------------- Phase 6.x compatibility layer ----------------

    def add_trace(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Store a generic internal trace payload.

        Stored under:
          {"timestamp": ..., "payload": {...}}

        Returns the stored entry.
        """
        if not isinstance(payload, dict):
            payload = {"value": payload}

        entry = {
            "timestamp": time.time(),
            "payload": payload,
        }
        self.snapshots.append(entry)
        self._save()
        return entry

    def write_trace(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Alias for add_trace(payload)."""
        return self.add_trace(payload)

    def log(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Alias for add_trace(payload)."""
        return self.add_trace(payload)

    def get_recent_traces(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Return recent traces in a normalized form:
          [{"ts": timestamp, "payload": {...}}, ...]
        """
        try:
            limit = int(limit)
        except Exception:
            limit = 100
        if limit <= 0:
            return []

        items = self.snapshots[-limit:]
        out: List[Dict[str, Any]] = []

        for it in items:
            if not isinstance(it, dict):
                continue
            ts = it.get("timestamp", None)

            # support both legacy cognitive snapshot and new payload traces
            if "payload" in it and isinstance(it.get("payload"), dict):
                payload = it["payload"]
            elif "snapshot" in it and isinstance(it.get("snapshot"), dict):
                payload = it["snapshot"]
            else:
                payload = {k: v for k, v in it.items() if k != "timestamp"}

            try:
                tsf = float(ts) if ts is not None else time.time()
            except Exception:
                tsf = time.time()

            out.append({"ts": tsf, "payload": payload})

        return out
