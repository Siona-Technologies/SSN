"""
Minimal HTTP embedding server for SIONA HttpEmbeddingProvider development.

Contract:
  POST /embed
    {"text": "..."} -> {"embedding": [...]}
    {"texts": ["...", "..."]} -> {"embeddings": [[...], ...]}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

_TOKEN_RE = re.compile(r"[^a-z0-9]+")
_WS_RE = re.compile(r"\s+")
DEFAULT_DIM = 64


def _normalize(text: str) -> str:
    return _WS_RE.sub(" ", (text or "").replace("\r", "\n")).strip().lower()


def _tokenize(text: str) -> List[str]:
    return [t for t in _TOKEN_RE.split(_normalize(text)) if len(t) >= 3]


def bow_embed(text: str, *, dim: int = DEFAULT_DIM) -> List[float]:
    vec = [0.0] * dim
    for tok in _tokenize(text):
        digest = hashlib.sha256(tok.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 0.0:
        return vec
    return [v / norm for v in vec]


class MockEmbedHandler(BaseHTTPRequestHandler):
    server_version = "SIONAMockEmbed/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        if os.getenv("SSN_MOCK_EMBED_QUIET") == "1":
            return
        super().log_message(fmt, *args)

    def _read_json(self) -> Tuple[bool, Dict[str, Any]]:
        try:
            length = int(self.headers.get("Content-Length") or "0")
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length > 0 else b""
        if not raw:
            return False, {}
        try:
            obj = json.loads(raw.decode("utf-8"))
        except json.JSONDecodeError:
            return False, {}
        return (True, obj) if isinstance(obj, dict) else (False, {})

    def _send_json(self, code: int, payload: Dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/health", "/v1/health"):
            self._send_json(200, {"ok": True, "service": "siona-mock-embed", "dim": DEFAULT_DIM})
            return
        self._send_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in ("/embed", "/v1/embed"):
            self._send_json(404, {"ok": False, "error": "not_found"})
            return

        ok, payload = self._read_json()
        if not ok:
            self._send_json(400, {"ok": False, "error": "invalid_json"})
            return

        texts = payload.get("texts")
        if isinstance(texts, list):
            embs = [bow_embed(str(t)) for t in texts]
            self._send_json(
                200,
                {
                    "embeddings": embs,
                    "meta": {"engine": "siona-mock-embed-v1", "dim": DEFAULT_DIM, "count": len(embs)},
                },
            )
            return

        text = payload.get("text")
        if not isinstance(text, str):
            self._send_json(400, {"ok": False, "error": "text_or_texts_required"})
            return

        emb = bow_embed(text)
        self._send_json(
            200,
            {
                "embedding": emb,
                "meta": {"engine": "siona-mock-embed-v1", "dim": DEFAULT_DIM},
            },
        )


def main() -> int:
    parser = argparse.ArgumentParser(description="SIONA mock embedding HTTP server")
    parser.add_argument("--host", default=os.getenv("SSN_MOCK_EMBED_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("SSN_MOCK_EMBED_PORT", "8002")))
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MockEmbedHandler)
    print(f"Mock embed server listening on http://{args.host}:{args.port}/embed")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[exit]")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
