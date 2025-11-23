"""
SSN Semantic Memory Store (Phase 3.5)

Upgraded to match MemoryHub + Orchestrator requirements.

Provides:
- store_fact()
- get_fact()
- delete_fact()
- list_facts()
"""

from __future__ import annotations
import json
import os
from typing import Any, Dict, Optional


DEFAULT_PATH = "ssn/data/semantic_memory.json"


class SemanticStore:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        self._facts: Dict[str, Any] = {}
        self._load()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _load(self) -> None:
        if not os.path.exists(self.path):
            self._facts = {}
            self._save()
            return

        with open(self.path, "r", encoding="utf-8") as f:
            try:
                self._facts = json.load(f)
            except json.JSONDecodeError:
                self._facts = {}

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._facts, f, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # PUBLIC API (aligned with Orchestrator + MemoryHub)
    # ------------------------------------------------------------------
    def store_fact(self, key: str, value: Any) -> None:
        """Create or update a semantic fact."""
        self._facts[key] = value
        self._save()

    def get_fact(self, key: str, default: Optional[Any] = None) -> Any:
        """Retrieve a stored fact."""
        return self._facts.get(key, default)

    def delete_fact(self, key: str) -> bool:
        """Delete a semantic fact."""
        if key in self._facts:
            del self._facts[key]
            self._save()
            return True
        return False

    def list_facts(self) -> Dict[str, Any]:
        """Return all semantic facts."""
        return dict(self._facts)
