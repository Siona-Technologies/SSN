"""Phase 3B — openai_chat dialect transport tests (deterministic mock only)."""

from __future__ import annotations

import json
import math
import os
import subprocess
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional
from unittest import mock

os.environ.setdefault("SSN_OFFLINE", "1")

from ssn.cognition.model_gateway import DeterministicModelProvider, ModelGateway, ModelRequest
from ssn.cognition.model_gateway.contracts import MessageRole, ModelMessage
from ssn.cognition.model_gateway.local_provider import (
    DIALECT_OPENAI_CHAT,
    DIALECT_SIONA_GENERATE,
    MAX_GATEWAY_TIMEOUT_S,
    MAX_MODEL_ID_CHARS,
    MAX_TRANSPORT_TIMEOUT_S,
    LocalOpenWeightProvider,
    LocalProviderError,
    compute_gateway_timeout_s,
    interpret_health_payload,
    normalize_gateway_timeout,
    normalize_transport_timeout,
    resolve_api_dialect,
    resolve_openai_chat_endpoints,
    resolve_verify_model_id,
    validate_endpoint_url,
    validate_openai_temperature,
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
        self.server.get_count = int(getattr(self.server, "get_count", 0)) + 1  # type: ignore[attr-defined]
        mode = getattr(self.server, "mode", "ok")
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        if path in {"/health", "/v1/health"}:
            if mode == "health_empty":
                self._write(200, {})
                return
            if mode == "health_status":
                self._write(200, {"status": "ok"})
                return
            if mode == "health_ok_bool":
                self._write(200, {"ok": True, "service": "mock"})
                return
            if mode == "health_nested_error":
                self._write(
                    200,
                    {
                        "status": "error",
                        "error": {"code": 503, "message": "Loading model", "nested": {"x": 1}},
                        "service": "x" * 400,
                    },
                )
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
            if mode == "models_empty_id":
                self._write(200, {"data": [{"id": ""}]})
                return
            if mode == "models_oversized_id":
                self._write(200, {"data": [{"id": "m" * (MAX_MODEL_ID_CHARS + 1)}]})
                return
            self._write(200, {"data": [{"id": model_id, "object": "model"}]})
            return
        self._write(404, {"error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        self.server.post_count = int(getattr(self.server, "post_count", 0)) + 1  # type: ignore[attr-defined]
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
        if mode == "missing_choices":
            self._write(200, {"usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}})
            return
        if mode == "empty_choices":
            self._write(200, {"choices": []})
            return
        if mode == "bad_choice":
            self._write(200, {"choices": ["nope"]})
            return
        if mode == "missing_message":
            self._write(200, {"choices": [{"finish_reason": "stop"}]})
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
        if mode == "tool_only":
            self._write(
                200,
                {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": "",
                                "tool_calls": [
                                    {"id": "1", "type": "function", "function": {"name": "x"}}
                                ],
                            },
                            "finish_reason": "tool_calls",
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
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
                                "tool_calls": [
                                    {"id": "1", "type": "function", "function": {"name": "x"}}
                                ],
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
        rf = body.get("response_format")
        if isinstance(rf, dict) and rf.get("type") == "json_object":
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
        self._httpd.get_count = 0  # type: ignore[attr-defined]
        self._httpd.post_count = 0  # type: ignore[attr-defined]
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
    def get_count(self) -> int:
        assert self._httpd is not None
        return int(getattr(self._httpd, "get_count", 0))

    @property
    def post_count(self) -> int:
        assert self._httpd is not None
        return int(getattr(self._httpd, "post_count", 0))

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
        self.assertTrue(interpret_health_payload({"ok": True})[0])
        self.assertTrue(interpret_health_payload({"status": "ok"})[0])
        self.assertFalse(interpret_health_payload({"ok": "true"})[0])

    def test_default_verify_model_id_by_dialect(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SSN_LOCAL_MODEL_VERIFY_MODEL_ID", None)
            self.assertTrue(resolve_verify_model_id(DIALECT_OPENAI_CHAT))
            self.assertFalse(resolve_verify_model_id(DIALECT_SIONA_GENERATE))

    def test_timeout_bounds(self):
        self.assertEqual(normalize_transport_timeout(20, explicit=True), 20.0)
        self.assertEqual(compute_gateway_timeout_s(20), 21.0)
        self.assertEqual(normalize_transport_timeout(119, explicit=True), 119.0)
        self.assertEqual(compute_gateway_timeout_s(119), 120.0)
        self.assertEqual(MAX_TRANSPORT_TIMEOUT_S, 119.0)
        self.assertEqual(MAX_GATEWAY_TIMEOUT_S, 120.0)
        for bad in (-1, 0, math.nan, math.inf, 120, 1e9):
            with self.assertRaises(LocalProviderError):
                normalize_transport_timeout(bad, explicit=True)
        with mock.patch.dict(os.environ, {"SSN_LOCAL_MODEL_TIMEOUT_S": "nan"}, clear=False):
            from ssn.cognition.model_gateway import local_provider as lp

            self.assertEqual(lp._parse_timeout(), 20.0)
        self.assertEqual(normalize_gateway_timeout(21.0), 21.0)
        with self.assertRaises(LocalProviderError):
            normalize_gateway_timeout(math.inf)
        with self.assertRaises(LocalProviderError):
            normalize_gateway_timeout(121)

    def test_temperature_bounds(self):
        self.assertEqual(validate_openai_temperature(0.0), 0.0)
        self.assertEqual(validate_openai_temperature(2.0), 2.0)
        for bad in (-0.1, 2.1, math.nan, math.inf):
            with self.assertRaises(LocalProviderError):
                validate_openai_temperature(bad)

    def test_invalid_ports(self):
        with self.assertRaises(LocalProviderError) as ctx:
            validate_endpoint_url("http://127.0.0.1:abc/generate")
        self.assertEqual(ctx.exception.category, "config")
        with self.assertRaises(LocalProviderError):
            validate_endpoint_url("http://127.0.0.1:0/generate")
        with self.assertRaises(LocalProviderError):
            validate_endpoint_url("http://127.0.0.1:65536/generate")
        validate_endpoint_url("http://127.0.0.1:8080/generate")
        validate_endpoint_url("http://[::1]:8080/generate")
        p = LocalOpenWeightProvider(
            endpoint="http://127.0.0.1:notaport/v1/chat/completions",
            model_id="m",
            api_dialect=DIALECT_OPENAI_CHAT,
            verify_model_id=False,
        )
        self.assertIsNotNone(p._config_error)
        self.assertIn("config:", str(p._config_error))


class TestOpenAIDialectBehaviour(unittest.TestCase):
    def test_request_response_mapping_and_token_cap(self):
        server = MockOpenAIServer(mode="ok").start()
        try:
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
            body = server.last_request
            self.assertEqual(body.get("model"), server.model_id)
            self.assertEqual(body.get("stream"), False)
            self.assertEqual(body.get("max_tokens"), 512)
            self.assertEqual(body["messages"][0]["role"], "system")
            for banned in ("tools", "context", "metadata", "tenant_id", "session_id", "trace_id"):
                self.assertNotIn(banned, body)
        finally:
            server.stop()

    def test_json_response_format_and_gateway_normalize(self):
        server = MockOpenAIServer(mode="ok").start()
        try:
            local = LocalOpenWeightProvider(
                endpoint=server.base_url,
                model_id=server.model_id,
                api_dialect=DIALECT_OPENAI_CHAT,
                verify_model_id=False,
            )
            gw = ModelGateway(providers=[local, DeterministicModelProvider()])
            req = ModelRequest.from_prompt("json please", system="sys")
            req.response_format = "json"
            resp = gw.complete(req)
            self.assertTrue(resp.healthy)
            self.assertIsInstance(resp.structured, dict)
            self.assertEqual(server.last_request.get("response_format"), {"type": "json_object"})
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
            server.set_mode("health_ok_bool")
            self.assertTrue(p.health().get("ok"))
            server.set_mode("health_empty")
            h = p.health()
            self.assertFalse(h.get("ok"))
            self.assertIn("health_contract_unrecognized", str(h.get("error")))
            server.set_mode("health_nested_error")
            h2 = p.health()
            self.assertFalse(h2.get("ok"))
            raw = h2.get("raw") or {}
            self.assertNotIn("error", raw)
            self.assertTrue(len(str(raw.get("service") or "")) <= 128)
        finally:
            server.stop()

    def test_model_id_verification_blocks_post(self):
        server = MockOpenAIServer(mode="models_mismatch").start()
        try:
            p = LocalOpenWeightProvider(
                endpoint=server.base_url,
                model_id=server.model_id,
                api_dialect=DIALECT_OPENAI_CHAT,
                verify_model_id=True,
            )
            before = server.post_count
            resp = p.generate(ModelRequest.from_prompt("x"))
            self.assertFalse(resp.healthy)
            self.assertEqual(resp.meta.get("error_category"), "model_mismatch")
            self.assertEqual(server.post_count, before)
            self.assertGreaterEqual(server.get_count, 1)
        finally:
            server.stop()

    def test_malformed_models_list_blocks_post(self):
        server = MockOpenAIServer(mode="models_bad").start()
        try:
            p = LocalOpenWeightProvider(
                endpoint=server.base_url,
                model_id=server.model_id,
                api_dialect=DIALECT_OPENAI_CHAT,
                verify_model_id=True,
            )
            before = server.post_count
            resp = p.generate(ModelRequest.from_prompt("x"))
            self.assertFalse(resp.healthy)
            self.assertEqual(server.post_count, before)
        finally:
            server.stop()

    def test_oversized_and_empty_server_model_ids(self):
        for mode in ("models_empty_id", "models_oversized_id"):
            server = MockOpenAIServer(mode=mode).start()
            try:
                p = LocalOpenWeightProvider(
                    endpoint=server.base_url,
                    model_id="valid-model",
                    api_dialect=DIALECT_OPENAI_CHAT,
                    verify_model_id=True,
                )
                before = server.post_count
                resp = p.generate(ModelRequest.from_prompt("x"))
                self.assertFalse(resp.healthy)
                self.assertEqual(server.post_count, before)
            finally:
                server.stop()

    def test_oversized_configured_model_id(self):
        p = LocalOpenWeightProvider(
            endpoint="http://127.0.0.1:9/v1/chat/completions",
            model_id="m" * (MAX_MODEL_ID_CHARS + 1),
            api_dialect=DIALECT_OPENAI_CHAT,
            verify_model_id=False,
        )
        self.assertIsNotNone(p._config_error)
        self.assertIn("model_id_invalid", str(p._config_error))

    def test_exact_model_match_allows_post(self):
        server = MockOpenAIServer(mode="ok").start()
        try:
            p = LocalOpenWeightProvider(
                endpoint=server.base_url,
                model_id=server.model_id,
                api_dialect=DIALECT_OPENAI_CHAT,
                verify_model_id=True,
            )
            resp = p.generate(ModelRequest.from_prompt("hello"))
            self.assertTrue(resp.healthy)
            self.assertEqual(server.post_count, 1)
        finally:
            server.stop()

    def test_response_shape_failures(self):
        for mode in (
            "missing_choices",
            "empty_choices",
            "bad_choice",
            "missing_message",
            "empty_content",
            "tool_only",
        ):
            server = MockOpenAIServer(mode=mode).start()
            try:
                p = LocalOpenWeightProvider(
                    endpoint=server.base_url,
                    model_id=server.model_id,
                    api_dialect=DIALECT_OPENAI_CHAT,
                    verify_model_id=False,
                )
                resp = p.generate(ModelRequest.from_prompt("x"))
                self.assertFalse(resp.healthy)
                self.assertEqual(resp.meta.get("error_category"), "malformed")
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
            caps = p.capabilities()
            self.assertFalse(caps.tools)
            self.assertFalse(caps.metadata["transport_capabilities"]["tools_proposals"])
            self.assertFalse(caps.streaming)
            self.assertFalse(caps.metadata.get("trained_siona_native"))
        finally:
            server.stop()

    def test_siona_generate_keeps_tools_proposals_transport_flag(self):
        server = MockLocalModelServer(mode="ok").start()
        try:
            p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="m")
            caps = p.capabilities()
            self.assertTrue(caps.metadata["transport_capabilities"]["tools_proposals"])
            self.assertFalse(caps.tools)
        finally:
            server.stop()

    def test_empty_messages_and_tool_role_only(self):
        server = MockOpenAIServer(mode="ok").start()
        try:
            local = LocalOpenWeightProvider(
                endpoint=server.base_url,
                model_id=server.model_id,
                api_dialect=DIALECT_OPENAI_CHAT,
                verify_model_id=False,
            )
            gw = ModelGateway(providers=[local, DeterministicModelProvider()])
            empty = ModelRequest(messages=[])
            resp = gw.complete(empty)
            self.assertTrue(resp.healthy)
            self.assertTrue(resp.fallback_used or resp.provider == DeterministicModelProvider.name)

            tool_only = ModelRequest(
                messages=[ModelMessage(role=MessageRole.TOOL, content="")]
            )
            before = server.post_count
            resp2 = local.generate(tool_only)
            self.assertFalse(resp2.healthy)
            self.assertEqual(resp2.meta.get("error_category"), "request")
            self.assertIn("empty_messages", str(resp2.meta.get("error")))
            self.assertEqual(server.post_count, before)

            ok = ModelRequest.from_prompt("hi", system="sys")
            resp3 = local.generate(ok)
            self.assertTrue(resp3.healthy)
        finally:
            server.stop()

    def test_temperature_rejection_fallback(self):
        server = MockOpenAIServer(mode="ok").start()
        try:
            local = LocalOpenWeightProvider(
                endpoint=server.base_url,
                model_id=server.model_id,
                api_dialect=DIALECT_OPENAI_CHAT,
                verify_model_id=False,
            )
            gw = ModelGateway(providers=[local, DeterministicModelProvider()])
            before = server.post_count
            for bad in (-1.0, 2.5, math.nan, math.inf):
                req = ModelRequest.from_prompt("hi")
                req.temperature = bad
                resp = gw.complete(req)
                self.assertTrue(resp.healthy)
                self.assertTrue(resp.fallback_used or resp.provider == DeterministicModelProvider.name)
            self.assertEqual(server.post_count, before)
        finally:
            server.stop()

    def test_explicit_timeout_rejects_non_finite(self):
        for bad in (-1, 0, math.nan, math.inf, 200):
            p = LocalOpenWeightProvider(
                endpoint="http://127.0.0.1:9/v1/chat/completions",
                model_id="m",
                api_dialect=DIALECT_OPENAI_CHAT,
                timeout_s=bad,
                verify_model_id=False,
            )
            self.assertIsNotNone(p._config_error)
            self.assertIn("invalid_timeout", str(p._config_error))

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
        out = adapter.generate(LLMRequest(prompt="hi", role="GUEST", context={}))
        self.assertTrue(isinstance(out.text, str))
        self.assertTrue(out.text)
        with self.assertRaises(LocalProviderError):
            ModelGatewayAsLLMProvider(gw, default_timeout_s=math.nan)

    def test_siona_generate_still_works_by_default(self):
        server = MockLocalModelServer(mode="ok").start()
        try:
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop("SSN_LOCAL_MODEL_API_DIALECT", None)
                p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="m")
                self.assertEqual(p.api_dialect, DIALECT_SIONA_GENERATE)
                resp = p.generate(ModelRequest.from_prompt("hi"))
                self.assertTrue(resp.healthy)
                self.assertTrue(p.health().get("ok"))
        finally:
            server.stop()

    def test_siona_health_rejects_empty_object(self):
        server = MockLocalModelServer(mode="ok").start()
        try:
            p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="m")
            assert p.transport is not None
            p.transport.get_json = lambda url: {}  # type: ignore[method-assign]
            h = p.health()
            self.assertFalse(h.get("ok"))
            self.assertIn("health_contract_unrecognized", str(h.get("error")))
        finally:
            server.stop()

    def test_no_process_spawn_apis(self):
        server = MockOpenAIServer(mode="ok").start()
        try:
            with mock.patch.object(subprocess, "Popen", side_effect=AssertionError("spawn")):
                with mock.patch.object(subprocess, "run", side_effect=AssertionError("spawn")):
                    with mock.patch.object(os, "system", side_effect=AssertionError("spawn")):
                        p = LocalOpenWeightProvider(
                            endpoint=server.base_url,
                            model_id=server.model_id,
                            api_dialect=DIALECT_OPENAI_CHAT,
                            verify_model_id=False,
                        )
                        self.assertTrue(p.generate(ModelRequest.from_prompt("hi")).healthy)
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
