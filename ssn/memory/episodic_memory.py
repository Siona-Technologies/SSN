"""
SSN Episodic Memory (Phase 3.5 – Unified Memory)

Stores a timeline of events such as:
{
    "timestamp": <float>,
    "type": <string>,
    "actor": <string>,
    "details": <dict>
}

Supports:
- record_event()
- add_event()              (compatibility alias)
- get_recent_events()
- search_events()
- get_all_events()
"""

from __future__ import annotations
import json
import os
import time
from typing import List, Dict, Any

DEFAULT_PATH = "ssn/data/episodic_memory.json"


class EpisodicMemory:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        # Initialize file if missing
        if not os.path.exists(self.path):
            with open(self.path, "w") as f:
                json.dump([], f)

        self._load()

    # ------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------
    def _load(self) -> None:
        """Load episodic memory from disk."""
        with open(self.path, "r") as f:
            try:
                self.events: List[Dict[str, Any]] = json.load(f)
            except json.JSONDecodeError:
                self.events = []

    def _save(self) -> None:
        """Persist episodic memory to disk."""
        with open(self.path, "w") as f:
            json.dump(self.events, f, indent=2)

    # ------------------------------------------------------
    # PUBLIC API
    # ------------------------------------------------------
    def record_event(self, event_type: str, actor: str, details: Dict[str, Any]):
        """
        Add a new event to episodic memory.
        """
        entry = {
            "timestamp": time.time(),
            "type": event_type,
            "actor": actor,
            "details": details,
        }

        self.events.append(entry)
        self._save()
        return entry

    # Backward compatibility for older tests
    def add_event(self, event_type: str, actor: str, details: Dict[str, Any]):
        """
        Alias for record_event().
        Older phases used add_event().
        """
        return self.record_event(event_type, actor, details)

    # ------------------------------------------------------
    # Retrieval APIs
    # ------------------------------------------------------
    def get_recent_events(self, limit: int = 5):
        """Return the most recent N events."""
        return self.events[-limit:]

    def search_events(self, keyword: str) -> List[Dict[str, Any]]:
        """Search event entries for a keyword."""
        keyword = keyword.lower()
        return [
            e for e in self.events
            if keyword in json.dumps(e).lower()
        ]

    def get_all_events(self) -> List[Dict[str, Any]]:
        """Return the entire episodic memory timeline."""
        return list(self.events)
