# ssn/knowledge/store.py

from __future__ import annotations

import json
import os
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from ssn.core.embedding_providers import (
    EmbeddingProvider,
    EmbeddingRequest,
    cosine_similarity,
    get_default_embedding_provider_from_env,
)
from ssn.knowledge.vector_index import VectorIndex, sidecar_path_for

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
    Local, file-backed knowledge store with optional embedding retrieval (Phase 5).

    Storage format:
      JSON Lines (one record per line) at SSN_KNOWLEDGE_PATH or default.
      Vector sidecar: {path}.vectors.json
    """

    def __init__(
        self,
        path: Optional[str] = None,
        *,
        embedding_provider: Optional[EmbeddingProvider] = None,
    ) -> None:
        env_path = os.getenv("SSN_KNOWLEDGE_PATH")
        p = path or (env_path if isinstance(env_path, str) and env_path.strip() else DEFAULT_KNOWLEDGE_PATH)
        self.path = p
        self._embedding_provider = embedding_provider

    def _provider(self) -> EmbeddingProvider:
        if self._embedding_provider is not None:
            return self._embedding_provider
        return get_default_embedding_provider_from_env()

    def _ensure_dir(self) -> None:
        d = os.path.dirname(self.path) or "."
        os.makedirs(d, exist_ok=True)

    @staticmethod
    def _record_document(rec: Dict[str, Any]) -> str:
        title = _safe_str(rec.get("title"))
        text = _safe_str(rec.get("text"))
        tags = rec.get("tags") if isinstance(rec.get("tags"), list) else []
        tag_s = " ".join(t for t in tags if isinstance(t, str))
        return _normalize_text(f"{title}\n{text}\n{tag_s}")

    @staticmethod
    def _keyword_score(qtok: set[str], rec: Dict[str, Any]) -> float:
        title = _safe_str(rec.get("title"))
        text = _safe_str(rec.get("text"))
        tags = rec.get("tags") if isinstance(rec.get("tags"), list) else []
        hay = f"{title}\n{text}\n{' '.join([t for t in tags if isinstance(t, str)])}"
        low = hay.lower()
        overlap = sum(1 for t in qtok if t in low)
        if overlap <= 0:
            return 0.0
        title_low = title.lower()
        title_overlap = sum(1 for t in qtok if t in title_low)
        return float(overlap) + (0.7 * float(title_overlap))

    def _scan_records(self, scan_limit: int) -> Tuple[List[Dict[str, Any]], int]:
        records: List[Dict[str, Any]] = []
        scanned = 0
        if not os.path.exists(self.path):
            return records, scanned
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
                if isinstance(rec, dict):
                    records.append(rec)
        return records, scanned

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
            qtok = set(t.lower() for t in q.split() if len(t) >= 3)

        provider = self._provider()
        provider_name = getattr(provider, "name", "unknown")
        use_http = provider_name.startswith("ssn-http")

        try:
            records, scanned = self._scan_records(scan_limit)
        except Exception as e:
            return {"ok": False, "error": {"code": "STORE_READ_FAILED", "message": str(e)}}

        if not records:
            return {
                "ok": True,
                "results": [],
                "scanned": scanned,
                "search_mode": "embedding" if use_http else "deterministic_embedding",
                "note": "No knowledge store file yet" if scanned == 0 else "No records matched",
            }

        try:
            query_vec = provider.embed(EmbeddingRequest(text=q)).vector
        except Exception as e:
            return self._search_keyword_only(
                q=q,
                qtok=qtok,
                records=records,
                scanned=scanned,
                top_k=top_k,
                include_text=include_text,
                snippet_chars=snippet_chars,
                note=f"Embedding failed; keyword fallback ({str(e)[:120]})",
            )

        dim = len(query_vec)
        sidecar = VectorIndex(
            sidecar_path_for(self.path),
            provider_name=provider_name,
            dim=dim,
        )
        if not sidecar.provider_matches(provider_name) or sidecar.dim != dim:
            sidecar = VectorIndex(sidecar_path_for(self.path), provider_name=provider_name, dim=dim)

        rec_by_kid: Dict[str, Dict[str, Any]] = {}
        scored: List[Tuple[float, float, float, Dict[str, Any]]] = []

        for rec in records:
            kid = _safe_str(rec.get("kid")) or f"row_{id(rec)}"
            rec_by_kid[kid] = rec
            doc = self._record_document(rec)
            fp = VectorIndex.fingerprint_text(doc)

            vec = sidecar.get(kid)
            if vec is None or sidecar.needs_refresh(kid=kid, text_fingerprint=fp):
                vec = provider.embed(EmbeddingRequest(text=doc)).vector
                sidecar.put(kid=kid, vector=vec, text_fingerprint=fp)

            embed_score = cosine_similarity(query_vec, vec)
            kw_score = self._keyword_score(qtok, rec)

            if use_http:
                final = (0.85 * embed_score) + (0.15 * min(kw_score / 5.0, 1.0))
            else:
                final = (0.55 * embed_score) + (0.45 * min(kw_score / 5.0, 1.0))

            if final <= 0.0 and kw_score <= 0.0 and embed_score <= 0.0:
                continue

            scored.append((final, embed_score, kw_score, rec))

        try:
            sidecar.persist()
        except Exception:
            pass

        scored.sort(key=lambda x: (-x[0], -x[1], _safe_str(x[3].get("kid"))))

        results: List[Dict[str, Any]] = []
        for final, embed_score, kw_score, rec in scored[:top_k]:
            title = _safe_str(rec.get("title"))
            text = _safe_str(rec.get("text"))
            snippet = _normalize_text(text)[:snippet_chars]
            item = {
                "kid": rec.get("kid"),
                "score": round(final, 6),
                "embedding_score": round(embed_score, 6),
                "keyword_score": round(kw_score, 6),
                "title": title,
                "snippet": snippet,
                "tags": rec.get("tags") if isinstance(rec.get("tags"), list) else [],
                "created_at": rec.get("created_at"),
            }
            if include_text:
                item["text"] = text
            results.append(item)

        return {
            "ok": True,
            "results": results,
            "scanned": scanned,
            "search_mode": "http_embedding" if use_http else "deterministic_embedding",
            "provider": provider_name,
        }

    def _search_keyword_only(
        self,
        *,
        q: str,
        qtok: set[str],
        records: List[Dict[str, Any]],
        scanned: int,
        top_k: int,
        include_text: bool,
        snippet_chars: int,
        note: str,
    ) -> Dict[str, Any]:
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for rec in records:
            kw = self._keyword_score(qtok, rec)
            if kw <= 0.0:
                continue
            scored.append((kw, rec))

        scored.sort(key=lambda x: (-x[0], _safe_str(x[1].get("kid"))))

        results: List[Dict[str, Any]] = []
        for score, rec in scored[:top_k]:
            title = _safe_str(rec.get("title"))
            text = _safe_str(rec.get("text"))
            snippet = _normalize_text(text)[:snippet_chars]
            item = {
                "kid": rec.get("kid"),
                "score": score,
                "embedding_score": 0.0,
                "keyword_score": score,
                "title": title,
                "snippet": snippet,
                "tags": rec.get("tags") if isinstance(rec.get("tags"), list) else [],
                "created_at": rec.get("created_at"),
            }
            if include_text:
                item["text"] = text
            results.append(item)

        return {
            "ok": True,
            "results": results,
            "scanned": scanned,
            "search_mode": "keyword_fallback",
            "note": note,
        }
