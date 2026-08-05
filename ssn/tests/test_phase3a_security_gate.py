"""Phase 3A final gate — security, redirects, sanitization, capabilities."""

from __future__ import annotations

import json
import os
import unittest
from unittest import mock

os.environ.setdefault("SSN_OFFLINE", "1")

from ssn.cognition.model_gateway import ModelMessage, ModelRequest, MessageRole
from ssn.cognition.model_gateway.local_provider import (
    LocalOpenWeightProvider,
    LocalProviderError,
    classify_endpoint_host,
    safe_endpoint_summary,
    validate_endpoint_url,
)
from ssn.cognition.model_gateway.mock_local_server import MockLocalModelServer
from ssn.cognition.model_gateway.registry import ModelRegistry, mock_ci_registry_payload
from ssn.cognition.model_gateway.sanitize import REDACTED, sanitize_model_request


class TestEndpointSecurity(unittest.TestCase):
    def test_loopback_accepted(self):
        validate_endpoint_url("http://127.0.0.1:9/generate", allow_remote=False)
        validate_endpoint_url("http://localhost:9/x", allow_remote=False)
        self.assertEqual(classify_endpoint_host("127.0.0.1"), "loopback")

    def test_remote_rejected_by_default(self):
        with self.assertRaises(LocalProviderError):
            validate_endpoint_url("http://example.com/generate", allow_remote=False)

    def test_embedded_credentials_rejected(self):
        with self.assertRaises(LocalProviderError) as ctx:
            validate_endpoint_url("http://user:pass@127.0.0.1:9/generate", allow_remote=False)
        self.assertEqual(ctx.exception.category, "security")

    def test_fragment_rejected(self):
        with self.assertRaises(LocalProviderError):
            validate_endpoint_url("http://127.0.0.1:9/generate#frag", allow_remote=False)

    def test_remote_with_override(self):
        url = validate_endpoint_url("http://example.com/generate", allow_remote=True)
        self.assertIn("example.com", url)
        summary = safe_endpoint_summary(url)
        self.assertEqual(summary["classification"], "remote")

    def test_redirect_remote_rejected(self):
        server = MockLocalModelServer(mode="redirect_remote").start()
        try:
            p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="mock")
            resp = p.generate(ModelRequest.from_prompt("x"))
            self.assertFalse(resp.healthy)
            self.assertEqual(resp.meta.get("error_category"), "redirect")
        finally:
            server.stop()

    def test_redirect_other_loopback_rejected(self):
        server = MockLocalModelServer(mode="redirect_loopback_other").start()
        try:
            p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="mock")
            resp = p.generate(ModelRequest.from_prompt("x"))
            self.assertFalse(resp.healthy)
            self.assertEqual(resp.meta.get("error_category"), "redirect")
        finally:
            server.stop()

    def test_health_redirect_rejected(self):
        server = MockLocalModelServer(mode="redirect_health_remote").start()
        try:
            p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="mock")
            h = p.health()
            self.assertFalse(h.get("ok"))
            self.assertIn("redirect", str(h.get("error") or ""))
        finally:
            server.stop()

    def test_endpoint_classification_reported(self):
        p = LocalOpenWeightProvider(endpoint="http://127.0.0.1:9/generate", model_id="m")
        self.assertEqual(p._endpoint_classification, "loopback")
        # health() may fail connection on closed port but classification must stay loopback
        h = p.health()
        self.assertEqual(h.get("endpoint_classification"), "loopback")
        self.assertTrue(h.get("endpoint_loopback"))
        p2 = LocalOpenWeightProvider(
            endpoint="http://example.com/generate",
            model_id="m",
            allow_remote=True,
        )
        self.assertEqual(p2._endpoint_classification, "remote")
        self.assertFalse(p2._endpoint_classification == "loopback")
        # Do not call health() — would attempt a real remote connection.
        summary = safe_endpoint_summary(p2._endpoint)
        self.assertEqual(summary["classification"], "remote")


class TestSanitizationBoundary(unittest.TestCase):
    def test_outgoing_payload_has_no_secrets(self):
        secret = "BOUNDARY_SECRET_VALUE_7c2e"
        os.environ["SSN_MASTER_KEY"] = secret
        server = MockLocalModelServer(mode="ok").start()
        try:
            p = LocalOpenWeightProvider(
                endpoint=server.generate_url,
                model_id="mock",
                capture_last_request=True,
            )
            req = ModelRequest(
                messages=[
                    ModelMessage(role=MessageRole.USER, content=f"master_key={secret}"),
                    ModelMessage(
                        role=MessageRole.ASSISTANT,
                        content=f"echo {secret}",
                        metadata={"password": secret, "locale": "en"},
                    ),
                ],
                system=f"Authorization: Bearer {secret}",
                context={"master_key": secret, "ok": True},
                metadata={"api_key": secret, "note": "x"},
                tools=[{"name": "demo", "parameters": {"password": secret}}],
            )
            resp = p.generate(req)
            self.assertTrue(resp.healthy)
            raw = p.transport.last_request_body or b""
            body = server.last_body() or {}
            decoded = json.dumps(body)
            self.assertNotIn(secret.encode("utf-8"), raw)
            self.assertNotIn(secret, decoded)
            self.assertNotIn(secret, raw.decode("utf-8", errors="replace"))
            # Redacted markers present in context/system path
            self.assertIn(REDACTED, decoded)
        finally:
            server.stop()
            os.environ.pop("SSN_MASTER_KEY", None)

    def test_sanitize_helper_strips_message_meta(self):
        secret = "META_SECRET_abc"
        req = ModelRequest(
            messages=[
                ModelMessage(
                    role=MessageRole.USER,
                    content="hi",
                    metadata={"authorization": secret, "locale": "en", "evil": secret},
                )
            ],
            context={"token": secret},
        )
        cleaned = sanitize_model_request(req)
        self.assertEqual(cleaned.messages[0].metadata.get("locale"), "en")
        self.assertNotIn("evil", cleaned.messages[0].metadata)
        self.assertEqual(cleaned.context.get("token"), REDACTED)
        self.assertEqual(cleaned.tenant_id, "")
        self.assertEqual(cleaned.session_id, "")


class TestCapabilitiesProvenance(unittest.TestCase):
    def test_missing_model_id(self):
        server = MockLocalModelServer(mode="ok").start()
        try:
            p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="")
            h = p.health()
            self.assertFalse(h.get("ok"))
            self.assertIn("model_id", str(h.get("error") or ""))
            resp = p.generate(ModelRequest.from_prompt("x"))
            self.assertFalse(resp.healthy)
        finally:
            server.stop()

    def test_missing_endpoint(self):
        p = LocalOpenWeightProvider(endpoint="", model_id="m")
        h = p.health()
        self.assertFalse(h.get("ok"))
        self.assertIn("endpoint", str(h.get("error") or ""))

    def test_unverified_conservative_capabilities(self):
        p = LocalOpenWeightProvider(endpoint="http://127.0.0.1:9/g", model_id="m")
        caps = p.capabilities()
        self.assertFalse(caps.tools)
        self.assertFalse(caps.structured_json)
        self.assertEqual(caps.context_window, 0)
        self.assertFalse(caps.metadata.get("trained_siona_native"))
        self.assertEqual(caps.metadata.get("capability_verification_status"), "unverified")
        self.assertFalse(caps.metadata.get("sync_mid_request_cancellation"))

    def test_mock_registry_capabilities(self):
        reg = ModelRegistry()
        reg.load_dict(mock_ci_registry_payload())
        entry = reg.get("mock-ci-open-weight")
        p = LocalOpenWeightProvider(
            endpoint="http://127.0.0.1:9/g",
            model_id="mock-ci-open-weight",
            registry_entry=entry,
        )
        caps = p.capabilities()
        self.assertEqual(caps.metadata.get("artifact_verification_status"), "mock")
        self.assertEqual(caps.metadata.get("capability_verification_status"), "unverified")
        self.assertFalse(caps.tools)
        self.assertFalse(caps.metadata.get("trained_siona_native"))
        self.assertTrue(caps.metadata.get("mock_registry"))

    def test_explicit_verified_capabilities_only(self):
        from ssn.cognition.model_gateway.registry import validate_entry_dict

        entry = validate_entry_dict(
            {
                "provider_id": "schema-fixture",
                "model_id": "cap-fixture",
                "mock": False,
                "siona_native": False,
                "artifact_verification_status": "unverified",
                "capability_verification_status": "verified",
                "capabilities": {
                    "chat": True,
                    "tools": False,
                    "structured_json": True,
                    "streaming": False,
                    "multimodal": False,
                    "context_window": 4096,
                },
                "notes": "schema fixture only",
            }
        )
        p = LocalOpenWeightProvider(
            endpoint="http://127.0.0.1:9/g",
            model_id="cap-fixture",
            registry_entry=entry,
        )
        caps = p.capabilities()
        self.assertTrue(caps.structured_json)
        self.assertFalse(caps.tools)
        self.assertEqual(caps.context_window, 4096)
        # Artefact status alone would not enable these — capability status does
        self.assertEqual(caps.metadata.get("capability_verification_status"), "verified")

    def test_no_unconfigured_model_id_string(self):
        p = LocalOpenWeightProvider(endpoint="", model_id=None)
        self.assertEqual(p.model_id, "")
        self.assertNotEqual(p.model_id, "unconfigured")


class TestAdversarialResponses(unittest.TestCase):
    def test_adversarial_tool_name(self):
        server = MockLocalModelServer(mode="adversarial_tools").start()
        try:
            p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="m")
            resp = p.generate(ModelRequest.from_prompt("x"))
            self.assertFalse(resp.healthy)
            self.assertIn(resp.meta.get("error_category"), {"size", "malformed"})
        finally:
            server.stop()

    def test_adversarial_usage_and_confidence(self):
        for mode in ("adversarial_usage", "adversarial_confidence", "oversized_tool_list"):
            server = MockLocalModelServer(mode=mode).start()
            try:
                p = LocalOpenWeightProvider(endpoint=server.generate_url, model_id="m")
                resp = p.generate(ModelRequest.from_prompt("x"))
                self.assertFalse(resp.healthy, msg=mode)
            finally:
                server.stop()


if __name__ == "__main__":
    unittest.main()
