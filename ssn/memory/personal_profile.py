"""
SSN Personal Profile (Phase 3.5)
Stores:
- preferences (Samson's stable choices)
- behaviors (decision tendencies, interaction styles)

Supports:
- update_preferences()
- update_behaviors()
- get_profile()
- dump()
"""

from __future__ import annotations
import json
import os
from typing import Dict, Any

DEFAULT_PATH = "ssn/data/personal_profile.json"


class PersonalProfile:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        # Initialize internal structure
        self.preferences: Dict[str, Any] = {}
        self.behaviors: Dict[str, Any] = {}

        self._load()

    # ---------------------------------------------------------
    # Internal load/save helpers
    # ---------------------------------------------------------
    def _load(self) -> None:
        if not os.path.exists(self.path):
            self._save()
            return

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.preferences = data.get("preferences", {})
                self.behaviors = data.get("behaviors", {})
        except json.JSONDecodeError:
            self.preferences = {}
            self.behaviors = {}
            self._save()

    def _save(self) -> None:
        data = {
            "preferences": self.preferences,
            "behaviors": self.behaviors,
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------
    def update_preferences(self, prefs: Dict[str, Any]) -> None:
        """Merge new preferences into the profile."""
        self.preferences.update(prefs)
        self._save()

    def update_behaviors(self, beh: Dict[str, Any]) -> None:
        """Merge new behavior traits into the profile."""
        self.behaviors.update(beh)
        self._save()

    def get_profile(self) -> Dict[str, Dict[str, Any]]:
        """Return full profile structure."""
        return {
            "preferences": self.preferences,
            "behaviors": self.behaviors,
        }

    def dump(self) -> Dict[str, Dict[str, Any]]:
        """Alias used by orchestrator for debugging output."""
        return self.get_profile()
