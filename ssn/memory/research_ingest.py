# ssn/memory/research_ingest.py

from __future__ import annotations

import time
from typing import Any, Dict, Optional


class ResearchIngestor:
    """
    Internal research ingestion pipeline.

    Purpose:
    - Allow SSN/SIONA to grow internal knowledge safely
    - Store research as semantic memory (facts / knowledge)
    - Preserve provenance, confidence, and timestamps
    - NEVER expose data directly to users
    - NEVER trigger external actions
    """

    def __init__(self, memory_hub) -> None:
        self.memory_hub = memory_hub

    # --------------------------------------------------
    # Public API (INTERNAL USE ONLY)
    # --------------------------------------------------

    def ingest(
        self,
        *,
        title: str,
        content: str,
        source: str,
        confidence: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Ingest a research artifact into semantic memory.

        Args:
            title: Short identifier for the research
            content: Main textual knowledge
            source: Provenance (e.g. "web", "paper", "dataset", "user")
            confidence: 0.0–1.0 confidence estimate
            metadata: Optional structured info

        Returns:
            Internal summary dict (NOT user-facing)
        """

        # -----------------------------
        # Validation (strict but simple)
        # -----------------------------
        if not isinstance(title, str) or not title.strip():
            return {"ok": False, "reason": "title_required"}

        if not isinstance(content, str) or not content.strip():
            return {"ok": False, "reason": "content_required"}

        if not isinstance(source, str) or not source.strip():
            return {"ok": False, "reason": "source_required"}

        try:
            conf = float(confidence)
        except Exception:
            conf = 0.5

        conf = max(0.0, min(conf, 1.0))

        # -----------------------------
        # Normalize record
        # -----------------------------
        record: Dict[str, Any] = {
            "type": "research",
            "title": title.strip()[:200],
            "content": content.strip(),
            "source": source.strip()[:100],
            "confidence": conf,
            "metadata": metadata or {},
            "ingested_at": time.time(),
        }

        key = f"research:{record['title']}"

        # -----------------------------
        # Store as semantic knowledge
        # -----------------------------
        # Prefer MemoryHub abstraction (prevents split-brain)
        try:
            self.memory_hub.remember_fact(key, record)
        except Exception:
            # Hard fail should not break cognition
            return {"ok": False, "reason": "semantic_store_failed"}

        # -----------------------------
        # Internal trace (non-user visible)
        # -----------------------------
        self._trace_ingest(record)

        return {
            "ok": True,
            "stored": True,
            "key": key,
            "title": record["title"],
            "source": record["source"],
            "confidence": record["confidence"],
        }

    # --------------------------------------------------
    # Internal helpers
    # --------------------------------------------------

    def _trace_ingest(self, record: Dict[str, Any]) -> None:
        """
        Write a bounded internal trace of research ingestion.
        This is NOT user-visible and NOT exposed via tools.
        """
        add = (
            getattr(self.memory_hub, "add_trace", None)
            or getattr(self.memory_hub, "write_trace", None)
            or getattr(self.memory_hub, "log_trace", None)
        )

        if not callable(add):
            return

        try:
            add(
                {
                    "type": "research_ingest",
                    "ts": time.time(),
                    "title": record["title"],
                    "source": record["source"],
                    "confidence": record["confidence"],
                }
            )
        except Exception:
            # Never allow tracing failure to break ingestion
            pass
