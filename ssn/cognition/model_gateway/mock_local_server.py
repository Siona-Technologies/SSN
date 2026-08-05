"""
Loopback-only mock local model HTTP server for Phase 3A transport tests.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional


class MockLocalModelHandler(BaseHTTPRequestHandler):
    server_version = "SionaMockLocalModel/1.0"

    # Behaviour knobs (set on server instance)
    # mode: ok | timeout | malformed | fail | oversized | json_ok

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def _read_json(self) -> Dict[str, Any]:
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        try:
            obj = json.loads(raw.decode("utf-8"))
            return obj if isinstance(obj, dict) else {}
        except Exception:
            return {}

    def _write(self, code: int, payload: Any) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        mode = getattr(self.server, "mode", "ok")
        if self.path.rstrip("/").endswith("health") or self.path in ("/health", "/v1/health"):
            if mode == "fail":
                self._write(503, {"ok": False, "error": "mock_unhealthy"})
                return
            self._write(200, {"ok": True, "service": "siona-mock-local-model"})
            return
        self._write(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        mode = getattr(self.server, "mode", "ok")
        body = self._read_json()
        if mode == "timeout":
            time.sleep(float(getattr(self.server, "timeout_sleep_s", 2.0)))
        if mode == "fail":
            self._write(500, {"ok": False, "error": "mock_fail"})
            return
        if mode == "malformed":
            raw = b"{not-json"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if mode == "oversized":
            huge = "x" * int(getattr(self.server, "oversized_bytes", 2_000_000))
            self._write(200, {"text": huge, "meta": {"engine": "mock-local"}})
            return
        prompt = str(body.get("prompt") or "")
        if mode == "json_ok" or str(body.get("response_format") or "") == "json":
            structured = {"ok": True, "echo": prompt[:80], "mock": True}
            self._write(
                200,
                {
                    "text": json.dumps(structured),
                    "structured": structured,
                    "meta": {"engine": "siona-mock-local-model", "mock": True},
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                },
            )
            return
        text = f'[MockLocal]: received "{prompt[:120]}"'
        self._write(
            200,
            {
                "text": text,
                "meta": {"engine": "siona-mock-local-model", "mock": True},
                "tool_calls": [],
                "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
            },
        )


class MockLocalModelServer:
    def __init__(self, *, mode: str = "ok") -> None:
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), MockLocalModelHandler)
        self._httpd.mode = mode  # type: ignore[attr-defined]
        self._thread: Optional[threading.Thread] = None

    @property
    def port(self) -> int:
        return int(self._httpd.server_address[1])

    @property
    def generate_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/generate"

    @property
    def health_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/health"

    def set_mode(self, mode: str) -> None:
        self._httpd.mode = mode  # type: ignore[attr-defined]

    def start(self) -> "MockLocalModelServer":
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread:
            self._thread.join(timeout=2.0)
