# ssn/knowledge/store.py

from __future__ import annotations

import json
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

DEFAULT_KNOWLEDGE_PATH = "ssn/knowledge/knowledge.jsonl"

_HARD_MAX_TEXT_CHARS = 200_000
_HARD_MAX_RECORDS_SCAN = 5_000

_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def _safe_str(x: Any) -> str:
    return x if isinstance(x, str) else ""


def _safe_list_dict(x: Any, cap: int) -> List[Dict[str, Any]]:
    if not isinstance(x, list):
        return []
    out: List[Dict[str, Any]] = []
    for it in x:
        if isinstance(it, dict):
            out.append(it)
        if len(out) >= cap:
            break
    return out


def _safe_list_str(x: Any, cap: int) -> List[str]:
    if not isinstance(x, list):
        return []
    out: List[str] = []
    for it in x:
        if isinstance(it, str):
            out.append(it)
        if len(out) >= cap:
            break
    return out


def _normalize_text(s: str) -> str:
    s = _safe_str(s)
    s = s.replace("\r", "\n")
    s = _WS_RE.sub(" ", s).strip()
    return s


def _tokenize(s: str) -> List[str]:
    s = _normalize_text(s).lower()
    toks = _TOKEN_RE.split(s)
    return [t for t in toks if len(t) >= 3]


class KnowledgeStore:
    """
    Local, file-backed knowledge store.

    Storage format:
      JSON Lines (one record per line) at SSN_KNOWLEDGE_PATH or default.

    Goals:
    - deterministic, offline-safe
    - no external deps
    - bounded search (top_k, scan_limit)
    """

    def __init__(self, path: Optional[str] = None) -> None:
        env_path = os.getenv("SSN_KNOWLEDGE_PATH")
        p = path or (env_path if isinstance(env_path, str) and env_path.strip() else DEFAULT_KNOWLEDGE_PATH)
        self.path = p

    def _ensure_dir(self) -> None:
        d = os.path.dirname(self.path) or "."
        os.makedirs(d, exist_ok=True)

    def promote(
        self,
        *,
        title: str,
        text: str,
        tags: List[str],
        sources: List[Dict[str, Any]],
        citations: List[Dict[str, Any]],
        provenance: Dict[str, Any],
    ) -> Dict[str, Any]:
        title_n = _normalize_text(title)[:240]
        text_n = _normalize_text(text)[:_HARD_MAX_TEXT_CHARS]

        if not title_n and not text_n:
            return {"ok": False, "error": {"code": "EMPTY_KNOWLEDGE", "message": "Both title and text are empty"}}

        now = time.time()
        kid = f"k_{int(now)}_{uuid.uuid4().hex[:10]}"

        rec = {
            "kid": kid,
            "title": title_n,
            "text": text_n,
            "tags": _safe_list_str(tags, 50),
            "sources": _safe_list_dict(sources, 80),
            "citations": _safe_list_dict(citations, 120),
            "provenance": provenance if isinstance(provenance, dict) else {},
            "created_at": now,
        }

        try:
            self._ensure_dir()
            with open(self.path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception as e:
            return {"ok": False, "error": {"code": "STORE_WRITE_FAILED", "message": str(e)}}

        return {"ok": True, "kid": kid, "status": "stored"}

    def search(
        self,
        *,
        query: str,
        top_k: int = 5,
        scan_limit: int = 500,
        include_text: bool = False,
        snippet_chars: int = 260,
    ) -> Dict[str, Any]:
        q = _normalize_text(query)
        if not q:
            return {"ok": False, "error": {"code": "INVALID_QUERY", "message": "Empty query"}}

        top_k = max(1, min(int(top_k or 5), 25))
        scan_limit = max(1, min(int(scan_limit or 500), _HARD_MAX_RECORDS_SCAN))
        snippet_chars = max(80, min(int(snippet_chars or 260), 800))

        qtok = set(_tokenize(q))
        if not qtok:
            qtok = set([t.lower() for t in q.split() if len(t) >= 3])

        scored: List[Tuple[float, Dict[str, Any]]] = []
        scanned = 0

        if not os.path.exists(self.path):
            return {"ok": True, "results": [], "scanned": 0, "note": "No knowledge store file yet"}

        try:
            with open(self.path, "r", encoding="utf-8") as f:
                for line in f:
                    if scanned >= scan_limit:
                        break
                    line = (line or "").strip()
                    if not line:
                        continue
                    scanned += 1
                    try:
                        rec = json.loads(line)
                    except Exception:
                        continue
                    if not isinstance(rec, dict):
                        continue

                    title = _safe_str(rec.get("title"))
                    text = _safe_str(rec.get("text"))
                    tags = rec.get("tags") if isinstance(rec.get("tags"), list) else []

                    hay = f"{title}\n{text}\n{' '.join([t for t in tags if isinstance(t, str)])}"
                    low = hay.lower()

                    # Simple deterministic scoring:
                    # - token overlap
                    # - title bonus
                    overlap = sum(1 for t in qtok if t in low)
                    if overlap <= 0:
                        continue

                    title_low = title.lower()
                    title_overlap = sum(1 for t in qtok if t in title_low)

                    score = float(overlap) + (0.7 * float(title_overlap))
                    scored.append((score, rec))
        except Exception as e:
            return {"ok": False, "error": {"code": "STORE_READ_FAILED", "message": str(e)}}

        scored.sort(key=lambda x: (-x[0], _safe_str(x[1].get("kid"))))

        results: List[Dict[str, Any]] = []
        for score, rec in scored[:top_k]:
            title = _safe_str(rec.get("title"))
            text = _safe_str(rec.get("text"))
            snippet = _normalize_text(text)[:snippet_chars]

            item = {
                "kid": rec.get("kid"),
                "score": score,
                "title": title,
                "snippet": snippet,
                "tags": rec.get("tags") if isinstance(rec.get("tags"), list) else [],
                "created_at": rec.get("created_at"),
            }

            if include_text:
                item["text"] = text

            results.append(item)

        return {"ok": True, "results": results, "scanned": scanned}
