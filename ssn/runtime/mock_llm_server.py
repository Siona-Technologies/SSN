"""
Minimal HTTP inference server for SIONA HttpLLMProvider development.

Implements the JSON contract from LLM_STRATEGY_V10.md:
  POST /generate  -> {"text": "...", "meta": {...}}

Uses stdlib only (no FastAPI). Safe for local dev on a normal PC.
"""

from __future__ import annotations

import argparse
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Tuple
from urllib.parse import urlparse


def _build_reply(payload: Dict[str, Any]) -> Dict[str, Any]:
    prompt = str(payload.get("prompt") or "")
    role = str(payload.get("role") or "GUEST").upper()
    ctx = payload.get("context") if isinstance(payload.get("context"), dict) else {}

    prefix = "[MockLLM OWNER]" if role == "OWNER" else "[MockLLM GUEST]"
    text = f"{prefix} {prompt}".strip()
    if ctx:
        text += f"\n(context keys: {sorted(ctx.keys())})"

    return {
        "text": text,
        "meta": {
            "engine": "siona-mock-llm-v1",
            "used_context": bool(ctx),
            "role": role,
        },
    }


class MockLLMHandler(BaseHTTPRequestHandler):
    server_version = "SIONAMockLLM/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        if os.getenv("SSN_MOCK_LLM_QUIET") == "1":
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
        if not isinstance(obj, dict):
            return False, {}
        return True, obj

    def _send_json(self, status: int, obj: Dict[str, Any]) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/health", "/healthz"):
            self._send_json(200, {"ok": True, "service": "siona-mock-llm"})
            return
        self._send_json(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path not in ("/generate", "/v1/generate"):
            self._send_json(404, {"ok": False, "error": "not_found"})
            return

        ok, payload = self._read_json()
        if not ok:
            self._send_json(400, {"ok": False, "error": "invalid_json"})
            return

        self._send_json(200, _build_reply(payload))


def main() -> None:
    parser = argparse.ArgumentParser(description="SIONA mock LLM HTTP server")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MockLLMHandler)
    print(f"SIONA mock LLM listening on http://{args.host}:{args.port}/generate")
    print("Set: SSN_LLM_PROVIDER=http SSN_LLM_ENDPOINT=http://127.0.0.1:{}/generate".format(args.port))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
