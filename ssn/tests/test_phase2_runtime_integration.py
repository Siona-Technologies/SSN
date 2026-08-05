"""
Phase 2 integration tests — modes, bridges, trace, no duplicates/leaks.
"""

from __future__ import annotations

import json
import os
import unittest
from unittest import mock

os.environ.setdefault("SSN_OFFLINE", "1")

from ssn.cognition.model_gateway import (
    DeterministicModelProvider,
    MalformedModelProvider,
    ModelGateway,
    ModelRequest,
    ModelResponse,
    MessageRole,
    ModelMessage,
)
from ssn.integration.runtime_modes import RuntimeMode, resolve_runtime_mode
from ssn.integration.trace_context import TraceContext
from ssn.integration.facade import IntegrationFacade
from ssn.integration.redaction import redact
from ssn.cognition.loop import CognitiveRuntime
from ssn.runtime.runtime_builder import SSNRuntimeBuilder
from ssn.interfaces.front_door import handle_user_message
from ssn.bootstrap import create_siona


class TestStructuredJsonStrict(unittest.TestCase):
    def test_valid_json_object_text(self):
        class JsonTextProvider:
            name = "json-text"

            def capabilities(self):
                return DeterministicModelProvider().capabilities()

            def health(self):
                return {"ok": True}

            def generate(self, request):
                return ModelResponse(
                    text='{"a": 1, "b": "x"}',
                    provider=self.name,
                    structured=None,
                    healthy=True,
                )

        gw = ModelGateway(providers=[JsonTextProvider()])
        req = ModelRequest.from_prompt("x")
        req.response_format = "json"
        resp = gw.complete(req)
        self.assertTrue(resp.healthy)
        self.assertEqual(resp.structured, {"a": 1, "b": "x"})

    def test_invalid_json_starting_with_brace(self):
        class BadBrace:
            name = "bad-brace"

            def capabilities(self):
                return DeterministicModelProvider().capabilities()

            def health(self):
                return {"ok": True}

            def generate(self, request):
                return ModelResponse(
                    text="{not-json",
                    provider=self.name,
                    structured=None,
                    healthy=True,
                )

        gw = ModelGateway(providers=[BadBrace(), DeterministicModelProvider()])
        req = ModelRequest.from_prompt("json please")
        req.response_format = "json"
        resp = gw.complete(req)
        self.assertTrue(resp.healthy)
        self.assertTrue(resp.fallback_used)
        self.assertIsInstance(resp.structured, dict)

    def test_json_array_rejected(self):
        class Arr:
            name = "arr"

            def capabilities(self):
                return DeterministicModelProvider().capabilities()

            def health(self):
                return {"ok": True}

            def generate(self, request):
                return ModelResponse(
                    text="[1,2,3]",
                    provider=self.name,
                    structured=None,
                    healthy=True,
                )

        gw = ModelGateway(providers=[Arr(), DeterministicModelProvider()])
        req = ModelRequest.from_prompt("json please")
        req.response_format = "json"
        resp = gw.complete(req)
        self.assertTrue(resp.fallback_used)
        self.assertIsInstance(resp.structured, dict)

    def test_empty_json_fallback(self):
        gw = ModelGateway(
            providers=[MalformedModelProvider(mode="empty"), DeterministicModelProvider()]
        )
        req = ModelRequest.from_prompt("json please")
        req.response_format = "json"
        resp = gw.complete(req)
        self.assertTrue(resp.healthy)
        self.assertTrue(resp.fallback_used)


class TestRuntimeModes(unittest.TestCase):
    def test_default_legacy(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SSN_COGNITIVE_MODE", None)
            self.assertEqual(resolve_runtime_mode(None), RuntimeMode.LEGACY)

    def test_invalid_falls_back(self):
        self.assertEqual(resolve_runtime_mode("not-a-mode"), RuntimeMode.LEGACY)

    def test_aliases(self):
        self.assertEqual(resolve_runtime_mode("shadow"), RuntimeMode.SHADOW)
        self.assertEqual(
            resolve_runtime_mode("cognitive_experimental"),
            RuntimeMode.COGNITIVE_EXPERIMENTAL,
        )


class TestCanonicalRuntime(unittest.TestCase):
    def test_shared_memory_world_tools_gateway(self):
        rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
        self.assertIsNotNone(rt.cognitive_runtime)
        self.assertIsNotNone(rt.integration)
        self.assertIs(rt.cognitive_runtime.memory.hub, rt.memory_hub)
        self.assertIs(rt.cognitive_runtime.world.world_model, rt.world_model)
        self.assertIs(rt.tool_registry, rt.orchestrator.tools)
        # Same model gateway instance on cognitive runtime / deps
        self.assertIs(
            rt.cognitive_runtime.model_gateway,
            rt.gateway.deps.get("model_gateway"),
        )
        # No per-request duplicate: build twice yields distinct runtimes but
        # each has one integration attached once.
        self.assertEqual(rt.gateway.deps.get("cognitive_mode"), rt.integration.mode.value)


class TestFrontDoorModes(unittest.TestCase):
    def test_legacy_compatible_answer(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "legacy", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            out = handle_user_message(
                "hello phase2",
                rt.gateway.deps,
                {"offline": True, "role": "GUEST"},
            )
            self.assertIn("Guest", out["answer"])
            # Exact legacy chat shape — no Phase-2 metadata on ordinary responses
            self.assertNotIn("runtime_mode", out)
            self.assertNotIn("trace_id", out)
            self.assertNotIn("integration", out)
            # Mode remains visible on health / diagnostic, not chat
            snap = rt.integration.diagnostic_snapshot()
            self.assertEqual(snap.get("runtime_mode"), "legacy")

    def test_shadow_does_not_change_answer_or_duplicate_model(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            before = rt.integration.metrics.model_requests
            out1 = handle_user_message(
                "shadow hello",
                rt.gateway.deps,
                {"offline": True},
            )
            out2 = handle_user_message(
                "shadow hello",
                rt.gateway.deps,
                {"offline": True},
            )
            self.assertEqual(out1["answer"], out2["answer"])
            self.assertEqual(out1.get("runtime_mode"), "shadow")
            self.assertFalse(out1.get("integration", {}).get("duplicate_model_call", True))
            # Shadow observations increment, not authoritative model_requests via gateway.complete
            self.assertGreaterEqual(
                rt.integration.metrics.model_shadow_observations, 1
            )
            self.assertGreaterEqual(
                rt.integration.metrics.duplicate_model_calls_prevented, 1
            )
            self.assertEqual(rt.integration.metrics.model_requests, before)

    def test_experimental_labelled(self):
        with mock.patch.dict(
            os.environ, {"SSN_COGNITIVE_MODE": "cognitive_experimental", "SSN_OFFLINE": "1"}
        ):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            out = handle_user_message("exp", rt.gateway.deps, {"offline": True})
            self.assertEqual(out.get("runtime_mode"), "cognitive_experimental")
            self.assertTrue(out.get("experimental"))
            self.assertIn("cognitive_experimental", out)
            self.assertIn("Guest", out["answer"])  # authoritative unchanged


class TestTraceAndIsolation(unittest.TestCase):
    def test_trace_continuity(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            tid = "trace-fixed-001"
            out = handle_user_message(
                "trace me",
                rt.gateway.deps,
                {"offline": True, "trace_id": tid, "session_id": "s1", "tenant_id": "t1"},
            )
            self.assertEqual(out.get("trace_id"), tid)

    def test_tenant_isolation_via_facade(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            handle_user_message(
                "alpha",
                rt.gateway.deps,
                {"offline": True, "tenant_id": "A", "session_id": "1"},
            )
            handle_user_message(
                "beta",
                rt.gateway.deps,
                {"offline": True, "tenant_id": "B", "session_id": "1"},
            )
            wa = rt.cognitive_runtime.workspaces.get("A", "1")
            wb = rt.cognitive_runtime.workspaces.get("B", "1")
            self.assertEqual(wa._context.get("last_user_text"), "alpha")
            self.assertEqual(wb._context.get("last_user_text"), "beta")


class TestBridgesNoDupNoLeak(unittest.TestCase):
    def test_tool_single_execution_count(self):
        cr = CognitiveRuntime.create()
        facade = IntegrationFacade.create(cognitive_runtime=cr, mode="shadow")
        tr = TraceContext(runtime_mode="shadow")
        eid = "exec-1"
        facade.observe_tool_execution(
            tool_name="tools.list",
            args={},
            execution_id=eid,
            ok=True,
            result_summary={"ok": True},
            trace=tr,
        )
        # Second observation with same id should not double-count execution
        facade.tools.on_completed(
            tool_name="tools.list",
            execution_id=eid,
            ok=True,
            result_summary={"ok": True},
            trace=tr,
            count_execution=True,
        )
        self.assertEqual(facade.metrics.tool_executions, 1)

    def test_world_update_once(self):
        cr = CognitiveRuntime.create()
        facade = IntegrationFacade.create(cognitive_runtime=cr, mode="shadow")
        tr = TraceContext(runtime_mode="shadow")
        self.assertTrue(
            facade.world.on_updated(update_id="u1", entity_count=1, event_count=1, trace=tr)
        )
        self.assertFalse(
            facade.world.on_updated(update_id="u1", entity_count=1, event_count=1, trace=tr)
        )
        self.assertEqual(facade.metrics.world_updates, 1)

    def test_no_queue_leak_after_requests(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            for i in range(25):
                handle_user_message(f"msg{i}", rt.gateway.deps, {"offline": True})
                self.assertEqual(rt.cognitive_runtime.bus.queue_depth, 0)

    def test_reflex_does_not_execute(self):
        cr = CognitiveRuntime.create()
        facade = IntegrationFacade.create(cognitive_runtime=cr, mode="shadow")
        tr = TraceContext(runtime_mode="shadow")
        # Force neuromorphic reflex path with high anomaly features
        facade._neuromorphic_shadow(user_input="x" * 200, trace=tr)
        # No tool registry execution occurred
        self.assertEqual(facade.metrics.tool_executions, 0)

    def test_secrets_redacted(self):
        payload = redact({"master_key": "SECRET", "ok": True, "authorization": "Bearer x"})
        self.assertEqual(payload["master_key"], "<redacted>")
        self.assertEqual(payload["authorization"], "<redacted>")
        snap = IntegrationFacade.create(
            cognitive_runtime=CognitiveRuntime.create(), mode="legacy"
        ).diagnostic_snapshot()
        blob = json.dumps(snap)
        self.assertNotIn("REAL_SECRET_VALUE", blob)
        self.assertNotIn("Bearer x", blob)


class TestPerceptionBridge(unittest.TestCase):
    def test_sense_tick_observation_shadow(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            from ssn.interfaces.contracts import InterfaceRequest
            from ssn.interfaces.handlers_sense_tick import handle_sense_tick

            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            # Without master key → blocked by policy (owner gate) — still no crash
            req = InterfaceRequest(action="sense_tick", role="GUEST", context={}, meta={})
            resp = handle_sense_tick(req, rt.gateway.deps)
            self.assertTrue(hasattr(resp, "ok"))


if __name__ == "__main__":
    unittest.main()
