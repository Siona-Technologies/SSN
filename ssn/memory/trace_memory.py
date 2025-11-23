"""
SSN Trace Memory (Phase 3.5)

Stores cognitive snapshots of each processing cycle.
Useful for:
- debugging brain decisions
- visualizing cognitive flow
- future meta-reasoning
"""

from __future__ import annotations
import json
import os
import time
from typing import Dict, Any

DEFAULT_PATH = "ssn/data/trace_memory.json"


class TraceMemory:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        if not os.path.exists(self.path):
            with open(self.path, "w") as f:
                json.dump([], f)

        self._load()

    # ---------------- internal ----------------

    def _load(self):
        with open(self.path, "r") as f:
            try:
                self.snapshots = json.load(f)
            except json.JSONDecodeError:
                self.snapshots = []

    def _save(self):
        with open(self.path, "w") as f:
            json.dump(self.snapshots, f, indent=2)

    # ---------------- public api ----------------

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
            "snapshot": packet,
        }

        self.snapshots.append(entry)
        self._save()

        return entry

    def recent(self, n: int = 5):
        """Return last n snapshots."""
        return self.snapshots[-n:]

    def all(self):
        return self.snapshots
