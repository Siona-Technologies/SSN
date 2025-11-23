"""
SSN Memory Hub (Phase 3.5 — Full Unified Memory Architecture)

This module unifies:
- Semantic memory (facts, knowledge)
- Episodic memory (events timeline)
- Personal profile (preferences + behaviors)
- Trace memory (cognitive snapshots)
- Backups (optional feature)

It is the HIGH-LEVEL memory brain used by the orchestrator.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional

from ssn.memory.semantic_store import SemanticStore
from ssn.memory.episodic_memory import EpisodicMemory
from ssn.memory.personal_profile import PersonalProfile
from ssn.memory.trace_memory import TraceMemory

try:
    from ssn.memory.backups import BackupManager
except ImportError:
    BackupManager = None


class MemoryHub:
    """
    Unified memory system used by SSN.
    """

    def __init__(self):
        # Core memory stores
        self.semantic = SemanticStore()
        self.episodic = EpisodicMemory()
        self.profile = PersonalProfile()
        self.trace = TraceMemory()

        # Optional backups
        self.backups = BackupManager() if BackupManager else None

    # ------------------------------------------------------------------
    # SEMANTIC MEMORY
    # ------------------------------------------------------------------
    def remember_fact(self, key: str, value: Any) -> None:
        self.semantic.set_fact(key, value)

    def recall_fact(self, key: str) -> Any:
        return self.semantic.get_fact(key)

    def recall_all_facts(self) -> Dict[str, Any]:
        return self.semantic.list_facts()

    def forget_fact(self, key: str) -> None:
        self.semantic.delete_fact(key)

    # ------------------------------------------------------------------
    # PERSONAL PROFILE MEMORY
    # ------------------------------------------------------------------
    def remember_preference(self, key: str, value: Any) -> None:
        self.profile.update_preferences({key: value})

    def remember_behavior(self, key: str, value: Any) -> None:
        self.profile.update_behaviors({key: value})

    def recall_profile(self) -> Dict[str, Dict[str, Any]]:
        return self.profile.get_profile()

    # ------------------------------------------------------------------
    # EPISODIC MEMORY
    # ------------------------------------------------------------------
    def log_event(self, event_type: str, actor: str, details: Dict[str, Any]) -> None:
        self.episodic.record_event(event_type, actor, details)

    def recall_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        return self.episodic.get_recent_events(limit)

    def search_events(self, query: str) -> List[Dict[str, Any]]:
        return self.episodic.search_events(query)

    # ------------------------------------------------------------------
    # TRACE MEMORY (new)
    # ------------------------------------------------------------------
    def store_trace(
        self,
        label: str,
        role: str,
        user_input: Any,
        brain_mode: str,
        routed_engine: Dict[str, Any],
        fusion_result: Dict[str, Any]
    ) -> None:
        """
        Saves a HIGH-LEVEL COGNITIVE SNAPSHOT of the entire thinking process.
        """
        snapshot = {
            "label": label,
            "role": role,
            "input_preview": str(user_input)[:200],
            "brain_mode": brain_mode,
            "routed_engine": routed_engine.get("engine"),
            "fusion_score": fusion_result.get("fusion_score"),
            "fusion_mode": fusion_result.get("mode"),
        }
        self.trace.store_cognitive_snapshot(snapshot)

    def recall_traces(self) -> List[Dict[str, Any]]:
        return self.trace.list_traces()

    # ------------------------------------------------------------------
    # HIGH-LEVEL INTERACTION LOGGING
    # ------------------------------------------------------------------
    def log_interaction(
        self,
        role: str,
        user_input: Any,
        brain_mode: str,
        routed_engine: Dict[str, Any],
        fusion_result: Dict[str, Any],
    ) -> None:
        """
        Logs the full brain interaction into episodic timeline.
        """
        actor = "Samson" if role == "OWNER" else "Guest"

        routed_name = None
        if "result" in routed_engine and isinstance(routed_engine["result"], dict):
            routed_name = routed_engine["result"].get("engine")

        details = {
            "role": role,
            "preview": str(user_input)[:200],
            "brain_mode": brain_mode,
            "routed_engine": routed_name,
            "fusion_mode": fusion_result.get("mode"),
            "fusion_score": fusion_result.get("fusion_score"),
        }

        self.log_event("interaction", actor, details)

    # ------------------------------------------------------------------
    # AUTOMATIC SEMANTIC INDEXING (Phase 3.5 — early NLP)
    # ------------------------------------------------------------------
    def auto_index_from_text(self, role: str, text: str) -> None:
        if role != "OWNER":
            return

        lower = text.lower()

        # simple pattern detection
        if "my favorite color is " in lower:
            try:
                color = lower.split("my favorite color is ")[1].split()[0]
                self.remember_fact("samson.favorite_color", color)
                self.remember_preference("favorite_color", color)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # BACKUPS
    # ------------------------------------------------------------------
    def create_backup(self, label: str = "snapshot") -> Optional[str]:
        if self.backups is None:
            return None

        snapshot = {
            "semantic": self.semantic.list_facts(),
            "profile": self.profile.get_profile(),
            "trace": self.trace.list_traces(),
        }
        return self.backups.create_backup(label, snapshot)

    def list_backups(self) -> Optional[List[str]]:
        if self.backups is None:
            return None
        return self.backups.list_backups()

    def load_backup(self, filename: str) -> Optional[Dict[str, Any]]:
        if self.backups is None:
            return None
        return self.backups.load_backup(filename)
