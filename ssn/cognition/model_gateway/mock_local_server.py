"""
Loopback-only mock local model HTTP server for Phase 3A transport tests.
"""

from __future__ import annotations

import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from urllib.parse import urlparse


class MockLocalModelHandler(BaseHTTPRequestHandler):
    server_version = "SionaMockLocalModel/1.0"

    # mode: ok | timeout | malformed | fail | oversized | json_ok
    #       | redirect_remote | redirect_loopback_other | redirect_health_remote
    #       | adversarial_tools | adversarial_usage | adversarial_confidence

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

    def _redirect(self, location: str, code: int = 302) -> None:
        self.send_response(code)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        mode = getattr(self.server, "mode", "ok")
        path = self.path.rstrip("/")
        if path.endswith("health") or self.path in ("/health", "/v1/health"):
            if mode == "redirect_health_remote":
                self._redirect("http://example.invalid/health")
                return
            if mode == "fail":
                self._write(503, {"ok": False, "error": "mock_unhealthy"})
                return
            self._write(200, {"ok": True, "service": "siona-mock-local-model"})
            return
        self._write(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        mode = getattr(self.server, "mode", "ok")
        body = self._read_json()
        # Capture last body for sanitization tests
        self.server.last_request_body = body  # type: ignore[attr-defined]
        self.server.last_raw_body = getattr(self, "_raw_stash", None)  # type: ignore[attr-defined]

        if mode == "redirect_remote":
            self._redirect("http://example.invalid/generate")
            return
        if mode == "redirect_loopback_other":
            # Different loopback origin (different port) — still rejected by default policy
            alt = int(getattr(self.server, "alt_loopback_port", 9))
            self._redirect(f"http://127.0.0.1:{alt}/generate")
            return
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
        if mode == "adversarial_tools":
            tools = [
                {
                    "name": "t" * 200,
                    "arguments": {"a": 1},
                    "call_id": "c1",
                    "confidence": 0.5,
                }
            ]
            self._write(200, {"text": "tools", "tool_calls": tools})
            return
        if mode == "adversarial_usage":
            self._write(
                200,
                {
                    "text": "usage",
                    "usage": {"prompt_tokens": -1, "completion_tokens": 1, "total_tokens": 0},
                },
            )
            return
        if mode == "adversarial_confidence":
            self._write(
                200,
                {
                    "text": "conf",
                    "tool_calls": [
                        {
                            "name": "tools.list",
                            "arguments": {},
                            "call_id": "c1",
                            "confidence": float("nan"),
                        }
                    ],
                },
            )
            return
        if mode == "oversized_tool_list":
            tools = [
                {"name": f"tool_{i}", "arguments": {}, "call_id": f"c{i}", "confidence": 0.5}
                for i in range(64)
            ]
            self._write(200, {"text": "many", "tool_calls": tools})
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
                    "finish_reason": "stop",
                },
            )
            return
        text = f'[MockLocal]: received "{prompt[:120]}"'
        if "EXACT_TOKEN_ALPHA" in prompt:
            text = "EXACT_TOKEN_ALPHA"
        self._write(
            200,
            {
                "text": text,
                "meta": {"engine": "siona-mock-local-model", "mock": True},
                "tool_calls": [],
                "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8, "latency_ms": 1.0},
                "finish_reason": "stop",
            },
        )


class MockLocalModelServer:
    def __init__(self, *, mode: str = "ok") -> None:
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), MockLocalModelHandler)
        self._httpd.mode = mode  # type: ignore[attr-defined]
        self._httpd.last_request_body = None  # type: ignore[attr-defined]
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

    def last_body(self) -> Optional[Dict[str, Any]]:
        return getattr(self._httpd, "last_request_body", None)

    def start(self) -> "MockLocalModelServer":
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self._httpd.shutdown()
        self._httpd.server_close()
        if self._thread:
            self._thread.join(timeout=2.0)
