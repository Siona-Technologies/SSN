from __future__ import annotations

"""
Lightweight vector sidecar for KnowledgeStore (stdlib + JSON; no heavy deps).
"""

import hashlib
import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

from ssn.core.embedding_providers import cosine_similarity


def sidecar_path_for(knowledge_path: str) -> str:
    return f"{knowledge_path}.vectors.json"


def _text_fingerprint(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class VectorIndex:
    """
    JSON sidecar mapping knowledge record ids -> embedding vectors.
    """

    def __init__(self, path: str, *, provider_name: str, dim: int) -> None:
        self.path = path
        self.provider_name = provider_name
        self.dim = dim
        self._entries: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            self._entries = {}
            return
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            self._entries = {}
            return
        if not isinstance(data, dict):
            self._entries = {}
            return
        entries = data.get("entries")
        self.provider_name = str(data.get("provider_name") or self.provider_name)
        self.dim = int(data.get("dim") or self.dim)
        self._entries = entries if isinstance(entries, dict) else {}

    def _save(self) -> None:
        d = os.path.dirname(self.path) or "."
        os.makedirs(d, exist_ok=True)
        payload = {
            "version": 1,
            "provider_name": self.provider_name,
            "dim": self.dim,
            "updated_at": time.time(),
            "entries": self._entries,
        }
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False)

    def get(self, kid: str) -> Optional[List[float]]:
        item = self._entries.get(kid)
        if not isinstance(item, dict):
            return None
        vec = item.get("vector")
        if not isinstance(vec, list):
            return None
        out = [float(x) for x in vec]
        return out if len(out) == self.dim else None

    def put(self, *, kid: str, vector: List[float], text_fingerprint: str) -> None:
        if len(vector) != self.dim:
            raise ValueError("vector dim mismatch")
        self._entries[kid] = {
            "vector": [float(x) for x in vector],
            "text_fingerprint": text_fingerprint,
        }

    def needs_refresh(self, *, kid: str, text_fingerprint: str) -> bool:
        item = self._entries.get(kid)
        if not isinstance(item, dict):
            return True
        return item.get("text_fingerprint") != text_fingerprint

    def provider_matches(self, provider_name: str) -> bool:
        return self.provider_name == provider_name

    def rank(
        self,
        *,
        query_vector: List[float],
        kid_vectors: List[Tuple[str, List[float]]],
        top_k: int,
    ) -> List[Tuple[float, str]]:
        scored: List[Tuple[float, str]] = []
        for kid, vec in kid_vectors:
            if len(vec) != len(query_vector):
                continue
            scored.append((cosine_similarity(query_vector, vec), kid))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return scored[:top_k]

    def persist(self) -> None:
        self._save()

    @staticmethod
    def fingerprint_text(text: str) -> str:
        return _text_fingerprint(text)
