"""Phase 3A — optional LocalOpenWeightProvider tests."""

from __future__ import annotations

import os
import unittest
from unittest import mock

os.environ.setdefault("SSN_OFFLINE", "1")

from ssn.cognition.model_gateway import DeterministicModelProvider, ModelGateway, ModelRequest
from ssn.cognition.model_gateway.local_provider import (
    LocalOpenWeightProvider,
    LocalProviderError,
    build_local_provider_from_env,
    local_provider_enabled,
    scrub_context_for_provider,
    validate_endpoint_url,
)
from ssn.cognition.model_gateway.mock_local_server import MockLocalModelServer


class TestLocalProviderConfig(unittest.TestCase):
    def test_disabled_by_default(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SSN_MODEL_PROVIDER", None)
            self.assertFalse(local_provider_enabled())
            self.assertIsNone(build_local_provider_from_env())

    def test_explicit_activation(self):
        server = MockLocalModelServer(mode="ok").start()
        try:
            with mock.patch.dict(
                os.environ,
                {
                    "SSN_MODEL_PROVIDER": "local",
                    "SSN_LOCAL_MODEL_ENDPOINT": server.generate_url,
                    "SSN_LOCAL_MODEL_ID": "mock-ci",
                },
                clear=False,
            ):
                self.assertTrue(local_provider_enabled())
                p = build_local_provider_from_env()
                self.assertIsNotNone(p)
                resp = p.generate(ModelRequest.from_prompt("hi"))
                self.assertTrue(resp.healthy)
                self.assertIn("MockLocal", resp.text)
        finally:
            server.stop()

    def test_loopback_accepted_remote_rejected(self):
        validate_endpoint_url("http://127.0.0.1:9/generate", allow_remote=False)
        validate_endpoint_url("http://localhost:9/generate", allow_remote=False)
        with self.assertRaises(LocalProviderError):
            validate_endpoint_url("http://example.com/generate", allow_remote=False)
        validate_endpoint_url("http://example.com/generate", allow_remote=True)

    def test_bad_scheme_rejected(self):
        with self.assertRaises(LocalProviderError):
            validate_endpoint_url("ftp://127.0.0.1/x", allow_remote=True)


class TestLocalProviderBehaviour(unittest.TestCase):
    def test_health_success_and_failure(self):
        server = MockLocalModelServer(mode="ok").start()
        try:
            p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="m")
            self.assertTrue(p.health().get("ok"))
            server.set_mode("fail")
            self.assertFalse(p.health().get("ok"))
        finally:
            server.stop()

    def test_timeout(self):
        server = MockLocalModelServer(mode="timeout").start()
        server._httpd.timeout_sleep_s = 1.5  # type: ignore[attr-defined]
        try:
            p = LocalOpenWeightProvider(
                endpoint=server.generate_url, model_id="m", timeout_s=0.2
            )
            resp = p.generate(ModelRequest.from_prompt("slow"))
            self.assertFalse(resp.healthy)
            self.assertIn(
                resp.meta.get("error_category"),
                {"timeout", "http"},
            )
        finally:
            server.stop()

    def test_malformed_and_oversized(self):
        server = MockLocalModelServer(mode="malformed").start()
        try:
            p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="m")
            resp = p.generate(ModelRequest.from_prompt("x"))
            self.assertFalse(resp.healthy)
            self.assertEqual(resp.meta.get("error_category"), "malformed")
        finally:
            server.stop()

        server = MockLocalModelServer(mode="oversized").start()
        try:
            p = LocalOpenWeightProvider(
                endpoint=server.generate_url, model_id="m", max_response_bytes=2048
            )
            resp = p.generate(ModelRequest.from_prompt("x"))
            self.assertFalse(resp.healthy)
            self.assertEqual(resp.meta.get("error_category"), "size")
        finally:
            server.stop()

    def test_structured_json_and_fallback(self):
        server = MockLocalModelServer(mode="json_ok").start()
        try:
            local = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="m")
            gw = ModelGateway(providers=[local, DeterministicModelProvider()])
            req = ModelRequest.from_prompt("json")
            req.response_format = "json"
            resp = gw.complete(req)
            self.assertTrue(resp.healthy)
            self.assertIsInstance(resp.structured, dict)
        finally:
            server.stop()

        # Unconfigured local is unhealthy → deterministic fallback
        local = LocalOpenWeightProvider(endpoint="")
        gw = ModelGateway(providers=[local, DeterministicModelProvider()])
        resp = gw.complete(ModelRequest.from_prompt("fallback"))
        self.assertTrue(resp.healthy)
        self.assertTrue(resp.fallback_used or resp.provider == DeterministicModelProvider.name)

    def test_secret_redaction_and_no_tool_execution(self):
        scrubbed = scrub_context_for_provider(
            {"master_key": "SECRET", "authorization": "Bearer x", "note": "ok"}
        )
        self.assertEqual(scrubbed.get("master_key"), "<redacted>")
        self.assertEqual(scrubbed.get("authorization"), "<redacted>")
        self.assertEqual(scrubbed.get("note"), "ok")
        # Provider never executes tools — proposals only in response objects
        server = MockLocalModelServer(mode="ok").start()
        try:
            p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="m")
            resp = p.generate(ModelRequest.from_prompt("tools?"))
            # No side-effect registry execution field
            self.assertNotIn("executed", resp.meta)
        finally:
            server.stop()

    def test_cancellation(self):
        from ssn.cognition.model_gateway import CancelToken

        server = MockLocalModelServer(mode="ok").start()
        try:
            p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="m")
            token = CancelToken()
            token.cancel()
            req = ModelRequest.from_prompt("x")
            req.cancel_token = token
            resp = p.generate(req)
            self.assertFalse(resp.healthy)
            self.assertEqual(resp.finish_reason, "cancelled")
        finally:
            server.stop()


if __name__ == "__main__":
    unittest.main()
