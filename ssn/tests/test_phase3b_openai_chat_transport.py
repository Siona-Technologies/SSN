"""Phase 3B — openai_chat dialect transport tests (deterministic mock only)."""

from __future__ import annotations

import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from unittest import mock

os.environ.setdefault("SSN_OFFLINE", "1")

from ssn.cognition.model_gateway import DeterministicModelProvider, ModelGateway, ModelRequest
from ssn.cognition.model_gateway.local_provider import (
    DIALECT_OPENAI_CHAT,
    DIALECT_SIONA_GENERATE,
    LocalOpenWeightProvider,
    LocalProviderError,
    interpret_health_payload,
    resolve_api_dialect,
    resolve_openai_chat_endpoints,
)
from ssn.cognition.model_gateway.mock_local_server import MockLocalModelServer
from ssn.cognition.model_gateway.adapters import ModelGatewayAsLLMProvider
from ssn.core.llm_providers import LLMRequest


class _OpenAIHandler(BaseHTTPRequestHandler):
    server_version = "SionaMockOpenAI/1.0"

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
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path in {"/health", "/v1/health"}:
            if mode == "health_empty":
                self._write(200, {})
                return
            if mode == "health_status":
                self._write(200, {"status": "ok"})
                return
            if mode == "fail":
                self._write(503, {"status": "error", "error": {"message": "loading"}})
                return
            self._write(200, {"status": "ok"})
            return
        if path == "/v1/models":
            model_id = getattr(self.server, "model_id", "Qwen3-1.7B-Q4_K_M.gguf")
            if mode == "models_mismatch":
                self._write(200, {"data": [{"id": "other-model"}]})
                return
            if mode == "models_bad":
                self._write(200, {"data": "nope"})
                return
            self._write(200, {"data": [{"id": model_id, "object": "model"}]})
            return
        self._write(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        mode = getattr(self.server, "mode", "ok")
        body = self._read_json()
        self.server.last_request_body = body  # type: ignore[attr-defined]
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path != "/v1/chat/completions":
            self._write(404, {"error": "not_found"})
            return
        if mode == "malformed":
            raw = b"{not-json"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
            return
        if mode == "empty_content":
            self._write(
                200,
                {
                    "choices": [{"message": {"role": "assistant", "content": ""}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 0, "total_tokens": 1},
                },
            )
            return
        if mode == "oversized":
            huge = "x" * int(getattr(self.server, "oversized_bytes", 2_000_000))
            self._write(
                200,
                {
                    "choices": [
                        {"message": {"role": "assistant", "content": huge}, "finish_reason": "stop"}
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                },
            )
            return
        if mode == "with_tools":
            self._write(
                200,
                {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "ignore tools",
                                "tool_calls": [{"id": "1", "type": "function", "function": {"name": "x"}}],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
                },
            )
            return
        if mode == "http_error":
            self._write(500, {"error": {"message": "boom"}})
            return
        content = "openai-mock-ok"
        if str(body.get("response_format") or "").find("json") >= 0 or (
            isinstance(body.get("response_format"), dict)
            and body.get("response_format", {}).get("type") == "json_object"
        ):
            content = '{"answer": true}'
        self._write(
            200,
            {
                "choices": [
                    {
                        "message": {"role": "assistant", "content": content},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5},
            },
        )


class MockOpenAIServer:
    def __init__(self, mode: str = "ok", model_id: str = "Qwen3-1.7B-Q4_K_M.gguf") -> None:
        self.mode = mode
        self.model_id = model_id
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> "MockOpenAIServer":
        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), _OpenAIHandler)
        self._httpd.mode = self.mode  # type: ignore[attr-defined]
        self._httpd.model_id = self.model_id  # type: ignore[attr-defined]
        self._httpd.last_request_body = None  # type: ignore[attr-defined]
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None

    def set_mode(self, mode: str) -> None:
        self.mode = mode
        if self._httpd is not None:
            self._httpd.mode = mode  # type: ignore[attr-defined]

    @property
    def base_url(self) -> str:
        assert self._httpd is not None
        host, port = self._httpd.server_address[:2]
        return f"http://{host}:{port}"

    @property
    def chat_url(self) -> str:
        return self.base_url + "/v1/chat/completions"

    @property
    def last_request(self) -> Dict[str, Any]:
        assert self._httpd is not None
        return dict(getattr(self._httpd, "last_request_body") or {})


class TestOpenAIDialectConfig(unittest.TestCase):
    def test_default_dialect_is_siona_generate(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SSN_LOCAL_MODEL_API_DIALECT", None)
            self.assertEqual(resolve_api_dialect(), DIALECT_SIONA_GENERATE)

    def test_unknown_dialect_fails_closed(self):
        with self.assertRaises(LocalProviderError):
            resolve_api_dialect("not_a_dialect")

    def test_openai_endpoint_derivation(self):
        chat, health, models = resolve_openai_chat_endpoints("http://127.0.0.1:8080")
        self.assertTrue(chat.endswith("/v1/chat/completions"))
        self.assertTrue(health.endswith("/health"))
        self.assertTrue(models.endswith("/v1/models"))
        chat2, _, _ = resolve_openai_chat_endpoints(
            "http://127.0.0.1:8080/v1/chat/completions"
        )
        self.assertEqual(chat, chat2)
        with self.assertRaises(LocalProviderError):
            resolve_openai_chat_endpoints("http://127.0.0.1:8080/generate")
        with self.assertRaises(LocalProviderError):
            resolve_openai_chat_endpoints("http://127.0.0.1:8080/v1/completions")

    def test_health_fail_closed_without_ok_or_status(self):
        ok, err = interpret_health_payload({})
        self.assertFalse(ok)
        self.assertEqual(err, "health_contract_unrecognized")
        ok2, _ = interpret_health_payload({"ok": True})
        self.assertTrue(ok2)
        ok3, _ = interpret_health_payload({"status": "ok"})
        self.assertTrue(ok3)
        ok4, _ = interpret_health_payload({"ok": "true"})
        self.assertFalse(ok4)


class TestOpenAIDialectBehaviour(unittest.TestCase):
    def test_request_response_mapping_and_token_cap(self):
        server = MockOpenAIServer(mode="ok").start()
        try:
            with mock.patch.dict(
                os.environ,
                {
                    "SSN_LOCAL_MODEL_API_DIALECT": "openai_chat",
                    "SSN_LOCAL_MODEL_VERIFY_MODEL_ID": "0",
                    "SSN_LOCAL_MODEL_MAX_TOKENS_CAP": "512",
                },
                clear=False,
            ):
                p = LocalOpenWeightProvider(
                    endpoint=server.base_url,
                    model_id=server.model_id,
                    api_dialect=DIALECT_OPENAI_CHAT,
                    verify_model_id=False,
                    max_tokens_cap=512,
                    capture_last_request=True,
                )
                req = ModelRequest.from_prompt("hello", system="sys")
                req.max_tokens = 4096
                resp = p.generate(req)
                self.assertTrue(resp.healthy)
                self.assertEqual(resp.text, "openai-mock-ok")
                body = server.last_request
                self.assertEqual(body.get("model"), server.model_id)
                self.assertEqual(body.get("stream"), False)
                self.assertEqual(body.get("max_tokens"), 512)
                self.assertEqual(body["messages"][0]["role"], "system")
                self.assertNotIn("tools", body)
                self.assertNotIn("context", body)
                self.assertNotIn("metadata", body)
                self.assertEqual(resp.meta.get("api_dialect"), DIALECT_OPENAI_CHAT)
        finally:
            server.stop()

    def test_health_status_ok_and_empty_unhealthy(self):
        server = MockOpenAIServer(mode="health_status").start()
        try:
            p = LocalOpenWeightProvider(
                endpoint=server.base_url,
                model_id=server.model_id,
                api_dialect=DIALECT_OPENAI_CHAT,
                verify_model_id=False,
            )
            self.assertTrue(p.health().get("ok"))
            server.set_mode("health_empty")
            h = p.health()
            self.assertFalse(h.get("ok"))
            self.assertIn("health_contract_unrecognized", str(h.get("error")))
        finally:
            server.stop()

    def test_model_id_verification(self):
        server = MockOpenAIServer(mode="models_mismatch").start()
        try:
            p = LocalOpenWeightProvider(
                endpoint=server.base_url,
                model_id=server.model_id,
                api_dialect=DIALECT_OPENAI_CHAT,
                verify_model_id=True,
            )
            resp = p.generate(ModelRequest.from_prompt("x"))
            self.assertFalse(resp.healthy)
            self.assertEqual(resp.meta.get("error_category"), "model_mismatch")
        finally:
            server.stop()

    def test_tool_calls_ignored_not_executed(self):
        server = MockOpenAIServer(mode="with_tools").start()
        try:
            p = LocalOpenWeightProvider(
                endpoint=server.base_url,
                model_id=server.model_id,
                api_dialect=DIALECT_OPENAI_CHAT,
                verify_model_id=False,
            )
            resp = p.generate(ModelRequest.from_prompt("x"))
            self.assertTrue(resp.healthy)
            self.assertEqual(resp.tool_calls, [])
            self.assertTrue(resp.meta.get("openai_tool_calls_ignored"))
        finally:
            server.stop()

    def test_empty_malformed_http_fallback(self):
        server = MockOpenAIServer(mode="empty_content").start()
        try:
            local = LocalOpenWeightProvider(
                endpoint=server.base_url,
                model_id=server.model_id,
                api_dialect=DIALECT_OPENAI_CHAT,
                verify_model_id=False,
            )
            gw = ModelGateway(providers=[local, DeterministicModelProvider()])
            resp = gw.complete(ModelRequest.from_prompt("x"))
            self.assertTrue(resp.healthy)
            self.assertTrue(resp.fallback_used or resp.provider == DeterministicModelProvider.name)
        finally:
            server.stop()

        server = MockOpenAIServer(mode="http_error").start()
        try:
            local = LocalOpenWeightProvider(
                endpoint=server.base_url,
                model_id=server.model_id,
                api_dialect=DIALECT_OPENAI_CHAT,
                verify_model_id=False,
            )
            resp = local.generate(ModelRequest.from_prompt("x"))
            self.assertFalse(resp.healthy)
            self.assertEqual(resp.meta.get("error_category"), "http")
        finally:
            server.stop()

    def test_gateway_timeout_margin_on_adapter(self):
        local = LocalOpenWeightProvider(
            endpoint="http://127.0.0.1:9/v1/chat/completions",
            model_id="m",
            api_dialect=DIALECT_OPENAI_CHAT,
            timeout_s=2.0,
            verify_model_id=False,
        )
        self.assertEqual(local.timeout_s, 2.0)
        self.assertEqual(local.gateway_timeout_s, 3.0)
        gw = ModelGateway(providers=[local, DeterministicModelProvider()])
        adapter = ModelGatewayAsLLMProvider(
            gw, name="test", default_timeout_s=local.gateway_timeout_s
        )
        # Should not raise; connection failure falls back deterministically.
        out = adapter.generate(LLMRequest(prompt="hi", role="GUEST", context={}))
        self.assertTrue(isinstance(out.text, str))
        self.assertTrue(out.text)

    def test_siona_generate_still_works_by_default(self):
        server = MockLocalModelServer(mode="ok").start()
        try:
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("SSN_LOCAL_MODEL_API_DIALECT", None)
                p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="m")
                self.assertEqual(p.api_dialect, DIALECT_SIONA_GENERATE)
                resp = p.generate(ModelRequest.from_prompt("hi"))
                self.assertTrue(resp.healthy)
                h = p.health()
                self.assertTrue(h.get("ok"))
        finally:
            server.stop()

    def test_siona_health_rejects_empty_object(self):
        # Fail-closed: unrecognized health JSON is unhealthy even for siona_generate.
        server = MockLocalModelServer(mode="ok").start()
        try:
            p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="m")
            # Monkeypatch transport get_json to return empty object.
            assert p.transport is not None
            p.transport.get_json = lambda url: {}  # type: ignore[method-assign]
            h = p.health()
            self.assertFalse(h.get("ok"))
            self.assertIn("health_contract_unrecognized", str(h.get("error")))
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
