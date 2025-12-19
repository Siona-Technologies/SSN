"""
SSN Memory Hub (Phase 3.5 — Full Unified Memory Architecture)

Unifies:
- Semantic memory (facts, knowledge)
- Episodic memory (events timeline)
- Personal profile (preferences + behaviors)
- Trace memory (cognitive snapshots + internal traces)
- Research ingestion (internal knowledge growth)
- Backups (optional)

Compatibility:
- Preserves existing public APIs
- Adds Phase 6.x adapters
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ssn.memory.semantic_store import SemanticStore
from ssn.memory.episodic_memory import EpisodicMemory
from ssn.memory.personal_profile import PersonalProfile
from ssn.memory.trace_memory import TraceMemory
from ssn.memory.research_ingest import ResearchIngestor

try:
    from ssn.memory.backups import BackupManager
except Exception:
    BackupManager = None


class MemoryHub:
    """
    Unified memory system used by SSN.
    """

    def __init__(self):
        # --------------------------------------------------
        # Core memory stores
        # --------------------------------------------------
        self.semantic = SemanticStore()
        self.episodic = EpisodicMemory()
        self.profile = PersonalProfile()

        # --------------------------------------------------
        # Trace memory (legacy + compatibility alias)
        # --------------------------------------------------
        self.trace = TraceMemory()
        self.trace_memory = self.trace

        # --------------------------------------------------
        # Research ingestion (internal-only)
        # --------------------------------------------------
        self.research = ResearchIngestor(self)

        # --------------------------------------------------
        # Optional backups
        # --------------------------------------------------
        self.backups = BackupManager() if BackupManager else None

    # ------------------------------------------------------------------
    # Internal helpers (safe cross-version calls)
    # ------------------------------------------------------------------
    @staticmethod
    def _try_call_first(obj: Any, names: List[str], *args, **kwargs):
        for n in names:
            fn = getattr(obj, n, None)
            if callable(fn):
                try:
                    return fn(*args, **kwargs)
                except Exception:
                    continue
        return None

    # ------------------------------------------------------------------
    # SEMANTIC MEMORY
    # ------------------------------------------------------------------
    def remember_fact(self, key: str, value: Any) -> None:
        self._try_call_first(
            self.semantic,
            ["set_fact", "store_fact", "remember_fact"],
            key,
            value,
        )

    def recall_fact(self, key: str) -> Any:
        return self._try_call_first(self.semantic, ["get_fact", "recall_fact"], key)

    def recall_all_facts(self) -> Dict[str, Any]:
        out = self._try_call_first(self.semantic, ["list_facts", "all_facts", "dump"])
        return out if isinstance(out, dict) else {}

    def forget_fact(self, key: str) -> None:
        self._try_call_first(
            self.semantic,
            ["delete_fact", "forget_fact", "remove_fact"],
            key,
        )

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
        self._try_call_first(
            self.episodic,
            ["record_event", "add_event", "log_event"],
            event_type,
            actor,
            details,
        )

    def recall_recent_events(self, limit: int = 10) -> List[Dict[str, Any]]:
        out = self._try_call_first(
            self.episodic,
            ["get_recent_events", "recent_events"],
            limit,
        )
        return out if isinstance(out, list) else []

    def search_events(self, query: str) -> List[Dict[str, Any]]:
        out = self._try_call_first(self.episodic, ["search_events", "find_events"], query)
        return out if isinstance(out, list) else []

    # ------------------------------------------------------------------
    # TRACE MEMORY (legacy cognitive snapshots)
    # ------------------------------------------------------------------
    def store_trace(
        self,
        label: str,
        role: str,
        user_input: Any,
        brain_mode: str,
        routed_engine: Dict[str, Any],
        fusion_result: Dict[str, Any],
    ) -> None:
        snapshot = {
            "label": label,
            "role": role,
            "input_preview": str(user_input)[:200],
            "brain_mode": brain_mode,
            "routed_engine": routed_engine.get("engine")
            if isinstance(routed_engine, dict)
            else None,
            "fusion_score": fusion_result.get("fusion_score")
            if isinstance(fusion_result, dict)
            else None,
            "fusion_mode": fusion_result.get("mode")
            if isinstance(fusion_result, dict)
            else None,
        }
        self._try_call_first(self.trace, ["store_cognitive_snapshot"], snapshot)

    def recall_traces(self) -> List[Dict[str, Any]]:
        out = self._try_call_first(self.trace, ["all", "list_traces"])
        if isinstance(out, list):
            return out
        snaps = getattr(self.trace, "snapshots", None)
        return snaps if isinstance(snaps, list) else []

    # ------------------------------------------------------------------
    # TRACE MEMORY (Phase 6.x adapters — FIXED)
    # ------------------------------------------------------------------
    def add_trace(self, payload: Dict[str, Any]) -> Any:
        return self._try_call_first(self.trace, ["add_trace", "write_trace", "log"], payload)

    def write_trace(self, payload: Dict[str, Any]) -> Any:
        return self.add_trace(payload)

    def log_trace(self, payload: Dict[str, Any]) -> Any:
        return self.add_trace(payload)

    def get_recent_traces(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Adapter-safe trace retrieval.
        Ensures research_ingest and tool traces are always visible.
        """

        # 1. Preferred API
        out = self._try_call_first(self.trace, ["get_recent_traces"], limit)
        if isinstance(out, list):
            return out[:limit]

        # 2. Alternative APIs
        out = self._try_call_first(self.trace, ["recent", "all", "list_traces"])
        if isinstance(out, list):
            return out[-limit:]

        # 3. Raw attribute fallback
        snaps = getattr(self.trace, "snapshots", None)
        if isinstance(snaps, list):
            return snaps[-limit:]

        return []

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
        actor = "Samson" if role == "OWNER" else "Guest"

        routed_name = None
        if isinstance(routed_engine, dict):
            routed_name = routed_engine.get("engine") or (
                routed_engine.get("result", {}).get("engine")
                if isinstance(routed_engine.get("result"), dict)
                else None
            )

        details = {
            "role": role,
            "preview": str(user_input)[:200],
            "brain_mode": brain_mode,
            "routed_engine": routed_name,
            "fusion_mode": fusion_result.get("mode")
            if isinstance(fusion_result, dict)
            else None,
            "fusion_score": fusion_result.get("fusion_score")
            if isinstance(fusion_result, dict)
            else None,
        }

        self.log_event("interaction", actor, details)

    # ------------------------------------------------------------------
    # AUTOMATIC SEMANTIC INDEXING (Phase 3.5 — early NLP)
    # ------------------------------------------------------------------
    def auto_index_from_text(self, role: str, text: str) -> None:
        if role != "OWNER":
            return
        if not isinstance(text, str) or not text.strip():
            return

        lower = text.lower()

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
            "semantic": self.recall_all_facts(),
            "profile": self.profile.get_profile(),
            "trace": self.recall_traces(),
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
