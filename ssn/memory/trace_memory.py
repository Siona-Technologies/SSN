from __future__ import annotations

import json
import os
import tempfile
import time
from typing import Any, Dict, List

DEFAULT_PATH = "ssn/data/trace_memory.json"


class TraceMemory:
    MAX_SNAPSHOTS = 5000

    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        if not os.path.exists(self.path):
            self._atomic_write_json(self.path, [])

        self.snapshots: List[Dict[str, Any]] = []
        self._load()

    # ---------------- internal ----------------

    @staticmethod
    def _atomic_write_json(path: str, data: Any) -> None:
        dir_name = os.path.dirname(path) or "."
        base_name = os.path.basename(path)

        fd = None
        tmp_path = None
        try:
            fd, tmp_path = tempfile.mkstemp(
                prefix=base_name + ".", suffix=".tmp", dir=dir_name
            )
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_path, path)

            try:
                dir_fd = os.open(dir_name, os.O_DIRECTORY)
                try:
                    os.fsync(dir_fd)
                finally:
                    os.close(dir_fd)
            except Exception:
                pass

        finally:
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
            self.snapshots = []

    def _save(self) -> None:
        if len(self.snapshots) > self.MAX_SNAPSHOTS:
            self.snapshots = self.snapshots[-self.MAX_SNAPSHOTS :]
        self._atomic_write_json(self.path, self.snapshots)

    # ---------------- original api ----------------

    def store_cognitive_snapshot(self, packet: Dict[str, Any]) -> Dict[str, Any]:
        entry = {
            "timestamp": time.time(),
            "snapshot": packet if isinstance(packet, dict) else {"value": packet},
        }
        self.snapshots.append(entry)
        self._save()
        return entry

    def recent(self, n: int = 5) -> List[Dict[str, Any]]:
        try:
            n = int(n)
        except Exception:
            n = 5
        if n <= 0:
            return []
        return self.snapshots[-n:]

    def all(self) -> List[Dict[str, Any]]:
        return self.snapshots

    # ---------------- Phase 6.x compatibility ----------------

    def add_trace(self, payload: Dict[str, Any]) -> Dict[str, Any]:
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
        return self.add_trace(payload)

    def log(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self.add_trace(payload)

    def get_recent_traces(self, limit: int = 100) -> List[Dict[str, Any]]:
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

            ts = it.get("timestamp", time.time())

            # normalize payload
            if "payload" in it and isinstance(it["payload"], dict):
                payload = it["payload"]
            elif "snapshot" in it and isinstance(it["snapshot"], dict):
                payload = it["snapshot"]
            else:
                payload = {}

            # 🔑 FLATTEN type for test + tooling compatibility
            entry = {
                "ts": ts,
                **payload,          # <-- THIS IS THE FIX
                "payload": payload, # still preserved
            }

            out.append(entry)

        return out
