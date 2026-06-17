from __future__ import annotations

"""
Embedding provider abstraction for SIONA knowledge / memory RAG.

Phase 5:
- DeterministicHashEmbedding (default, CI-safe)
- HttpEmbeddingProvider (local/remote embed server)
"""

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol
from urllib import error as urllib_error
from urllib import request as urllib_request

_WS_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[^a-z0-9]+")

DEFAULT_EMBED_DIM = 64


@dataclass(frozen=True)
class EmbeddingRequest:
    text: str


@dataclass(frozen=True)
class EmbeddingResponse:
    vector: List[float]
    meta: Dict[str, Any]


class EmbeddingProvider(Protocol):
    name: str
    dim: int

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        ...

    def embed_batch(self, texts: List[str]) -> List[EmbeddingResponse]:
        ...


def _normalize_text(s: str) -> str:
    s = s if isinstance(s, str) else ""
    s = s.replace("\r", "\n")
    return _WS_RE.sub(" ", s).strip()


def _l2_normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 0.0:
        return vec[:]
    return [v / norm for v in vec]


def _hash_to_vector(text: str, *, dim: int) -> List[float]:
    """
    Deterministic pseudo-embedding from SHA-256 chunks (stdlib only).
    """
    dim = max(8, min(int(dim), 512))
    raw = _normalize_text(text).encode("utf-8")
    out: List[float] = []
    counter = 0
    while len(out) < dim:
        digest = hashlib.sha256(raw + counter.to_bytes(4, "little")).digest()
        for i in range(0, len(digest) - 3, 4):
            val = int.from_bytes(digest[i : i + 4], "little", signed=False)
            out.append((val / 2**32) * 2.0 - 1.0)
            if len(out) >= dim:
                break
        counter += 1
    return _l2_normalize(out[:dim])


class DeterministicHashEmbedding:
    name = "ssn-deterministic-hash-v1"
    dim = DEFAULT_EMBED_DIM

    def __init__(self, *, dim: int = DEFAULT_EMBED_DIM) -> None:
        self.dim = max(8, min(int(dim), 512))

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        text = _normalize_text(request.text)
        vec = _hash_to_vector(text, dim=self.dim)
        return EmbeddingResponse(
            vector=vec,
            meta={"provider": self.name, "dim": self.dim, "deterministic": True},
        )

    def embed_batch(self, texts: List[str]) -> List[EmbeddingResponse]:
        return [self.embed(EmbeddingRequest(text=t)) for t in texts]


class HttpEmbeddingProvider:
    """
    HTTP embedding client.

    Contract (POST JSON):
      Request:  {"text": "..."}  OR  {"texts": ["...", "..."]}
      Response: {"embedding": [...]} OR {"embeddings": [[...], ...]}
    """

    name = "ssn-http-embedding-v1"
    dim = DEFAULT_EMBED_DIM

    def __init__(
        self,
        *,
        endpoint: Optional[str] = None,
        fallback: Optional[EmbeddingProvider] = None,
        timeout_sec: float = 30.0,
    ) -> None:
        env_url = (os.getenv("SSN_EMBEDDING_ENDPOINT") or "").strip()
        self.endpoint = (endpoint or env_url).strip().rstrip("/")
        self.fallback = fallback or DeterministicHashEmbedding()
        self.timeout_sec = float(timeout_sec)

    def _post(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        if not self.endpoint:
            raise RuntimeError("SSN_EMBEDDING_ENDPOINT not set")

        data = json.dumps(payload).encode("utf-8")
        req = urllib_request.Request(
            self.endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=self.timeout_sec) as resp:
            body = resp.read().decode("utf-8")
        obj = json.loads(body)
        if not isinstance(obj, dict):
            raise ValueError("embedding response must be a JSON object")
        return obj

    def _vectors_from_response(self, obj: Dict[str, Any], *, batch: bool) -> List[List[float]]:
        if batch:
            embs = obj.get("embeddings")
            if not isinstance(embs, list):
                raise ValueError("response missing embeddings list")
            out: List[List[float]] = []
            for item in embs:
                if not isinstance(item, list):
                    raise ValueError("invalid embedding vector")
                out.append([float(x) for x in item])
            return out

        emb = obj.get("embedding")
        if not isinstance(emb, list):
            raise ValueError("response missing embedding vector")
        return [[float(x) for x in emb]]

    def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        text = _normalize_text(request.text)
        try:
            obj = self._post({"text": text})
            vec = self._vectors_from_response(obj, batch=False)[0]
            vec = _l2_normalize(vec)
            self.dim = len(vec)
            return EmbeddingResponse(
                vector=vec,
                meta={
                    "provider": self.name,
                    "dim": len(vec),
                    "endpoint": self.endpoint,
                    "deterministic": False,
                },
            )
        except Exception as exc:
            fb = self.fallback.embed(EmbeddingRequest(text=text))
            meta = dict(fb.meta)
            meta["fallback"] = True
            meta["fallback_reason"] = str(exc)[:200]
            return EmbeddingResponse(vector=fb.vector, meta=meta)

    def embed_batch(self, texts: List[str]) -> List[EmbeddingResponse]:
        cleaned = [_normalize_text(t) for t in texts]
        if not cleaned:
            return []
        try:
            obj = self._post({"texts": cleaned})
            vecs = self._vectors_from_response(obj, batch=True)
            if len(vecs) != len(cleaned):
                raise ValueError("embeddings length mismatch")
            out: List[EmbeddingResponse] = []
            for text, vec in zip(cleaned, vecs):
                vec = _l2_normalize(vec)
                self.dim = len(vec)
                out.append(
                    EmbeddingResponse(
                        vector=vec,
                        meta={
                            "provider": self.name,
                            "dim": len(vec),
                            "endpoint": self.endpoint,
                            "deterministic": False,
                        },
                    )
                )
            return out
        except Exception:
            return self.fallback.embed_batch(cleaned)


def get_default_embedding_provider_from_env() -> EmbeddingProvider:
    """
    Env:
      SSN_EMBEDDING_PROVIDER=deterministic|http  (default: deterministic)
      SSN_EMBEDDING_ENDPOINT=http://127.0.0.1:8002/embed
      SSN_EMBEDDING_DIM=64
    """
    name = (os.getenv("SSN_EMBEDDING_PROVIDER") or "deterministic").strip().lower()
    dim = int(os.getenv("SSN_EMBEDDING_DIM") or DEFAULT_EMBED_DIM)

    if name == "http":
        return HttpEmbeddingProvider(fallback=DeterministicHashEmbedding(dim=dim))

    return DeterministicHashEmbedding(dim=dim)


def cosine_similarity(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na <= 0.0 or nb <= 0.0:
        return 0.0
    return dot / (na * nb)
