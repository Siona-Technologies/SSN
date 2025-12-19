# ssn/memory/research_query.py

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional


class ResearchQuery:
    """
    Read-only research retrieval layer.

    Responsibilities:
    - Query previously ingested research records
    - Apply confidence / source / freshness filters
    - Return CANDIDATES, never final answers
    - Never write to memory
    - Never expose directly to user interfaces
    """

    def __init__(self, memory_hub) -> None:
        self.memory_hub = memory_hub

    # --------------------------------------------------
    # Public API
    # --------------------------------------------------

    def search(
        self,
        query: str,
        *,
        min_confidence: float = 0.6,
        sources: Optional[List[str]] = None,
        limit: int = 5,
        max_age_seconds: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search ingested research records.

        Args:
            query: Free-text query
            min_confidence: Minimum confidence threshold (0.0–1.0)
            sources: Optional list of allowed sources (e.g. ["web", "paper"])
            limit: Max number of results
            max_age_seconds: Optional freshness filter

        Returns:
            List of matching research records (bounded, ordered)
        """

        if not isinstance(query, str) or not query.strip():
            return []

        q = query.lower().strip()
        now = time.time()

        # Pull all semantic facts
        facts = self.memory_hub.recall_all_facts()
        if not isinstance(facts, dict):
            return []

        results: List[Dict[str, Any]] = []

        for key, value in facts.items():
            if not isinstance(key, str):
                continue

            # Only research records
            if not key.startswith("research:"):
                continue

            if not isinstance(value, dict):
                continue

            # Required fields
            content = str(value.get("content", "")).lower()
            title = str(value.get("title", "")).lower()
            confidence = float(value.get("confidence", 0.0))
            source = value.get("source")

            # Confidence filter
            if confidence < min_confidence:
                continue

            # Source filter
            if sources and source not in sources:
                continue

            # Freshness filter
            if max_age_seconds is not None:
                ingested_at = value.get("ingested_at")
                if isinstance(ingested_at, (int, float)):
                    if now - ingested_at > max_age_seconds:
                        continue

            # Basic relevance check
            if q not in content and q not in title:
                continue

            results.append(value)

        # Sort by confidence DESC, then recency DESC
        results.sort(
            key=lambda r: (
                float(r.get("confidence", 0.0)),
                float(r.get("ingested_at", 0.0)),
            ),
            reverse=True,
        )

        return results[: max(1, min(limit, 20))]
