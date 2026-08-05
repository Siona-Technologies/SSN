"""
Phase 2 final hardening — legacy shape, routing dedupe, trace, async safety.
"""

from __future__ import annotations

import asyncio
import os
import re
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("SSN_OFFLINE", "1")

from ssn.cognition.loop import CognitiveRuntime
from ssn.integration.facade import IntegrationFacade
from ssn.integration.trace_context import TraceContext
from ssn.interfaces.contracts import InterfaceRequest
from ssn.interfaces.front_door import handle_user_message
from ssn.interfaces.handlers_sense_tick import handle_sense_tick
from ssn.interfaces.handlers_tools import handle_run_tool
from ssn.runtime.runtime_builder import SSNRuntimeBuilder

ROOT = Path(__file__).resolve().parents[2]

# Pre-Phase-2 / Phase-1 Front Door success path keys (LLM-only guest chat).
LEGACY_FRONT_DOOR_KEYS = frozenset({"answer", "degraded", "used_tools", "session_state"})
PHASE2_CHAT_META_KEYS = frozenset(
    {
        "runtime_mode",
        "trace_id",
        "integration",
        "cognitive_experimental",
        "experimental",
    }
)


def _collect_events(bus):
    seen = []

    async def _handler(event):
        seen.append(event)

    unsub = bus.subscribe(_handler, name="phase2-harden-collector")
    return seen, unsub


class TestLegacyResponseKeyCompatibility(unittest.TestCase):
    def test_exact_legacy_key_set(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "legacy", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            out = handle_user_message(
                "legacy key check",
                rt.gateway.deps,
                {"offline": True, "role": "GUEST"},
            )
            self.assertEqual(frozenset(out.keys()), LEGACY_FRONT_DOOR_KEYS)

    def test_no_phase2_metadata_in_legacy_chat(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "legacy", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            out = handle_user_message("no meta", rt.gateway.deps, {"offline": True})
            for k in PHASE2_CHAT_META_KEYS:
                self.assertNotIn(k, out)


class TestRoutingEventDedup(unittest.TestCase):
    def test_exactly_one_routing_selected_shadow(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            seen, unsub = _collect_events(rt.cognitive_runtime.bus)
            try:
                tid = "route-trace-001"
                out = handle_user_message(
                    "route once",
                    rt.gateway.deps,
                    {
                        "offline": True,
                        "trace_id": tid,
                        "correlation_id": tid,
                        "session_id": "s-route",
                        "tenant_id": "t-route",
                    },
                )
                routing = [e for e in seen if e.event_type == "routing.selected"]
                self.assertEqual(len(routing), 1)
                self.assertEqual(routing[0].trace_id, tid)
                self.assertEqual(routing[0].correlation_id, tid)
                inputs = [e for e in seen if e.event_type == "input.text"]
                responses = [e for e in seen if e.event_type == "response.completed"]
                self.assertEqual(len(inputs), 1)
                self.assertEqual(len(responses), 1)
                self.assertEqual(inputs[0].trace_id, tid)
                self.assertEqual(responses[0].trace_id, tid)
                self.assertEqual(inputs[0].correlation_id, tid)
                self.assertEqual(responses[0].correlation_id, tid)
                self.assertEqual(out.get("trace_id"), tid)
            finally:
                unsub()

    def test_no_routing_event_in_legacy(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "legacy", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            seen, unsub = _collect_events(rt.cognitive_runtime.bus)
            try:
                handle_user_message("legacy route silence", rt.gateway.deps, {"offline": True})
                routing = [e for e in seen if e.event_type == "routing.selected"]
                self.assertEqual(len(routing), 0)
            finally:
                unsub()

    def test_brain_router_has_no_integration_observer(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            self.assertFalse(callable(getattr(rt.brain_router, "integration_observer", None)))


class TestTraceContinuity(unittest.TestCase):
    def test_one_trace_across_chat_child_events(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            seen, unsub = _collect_events(rt.cognitive_runtime.bus)
            try:
                tid = "full-trace-continuity"
                handle_user_message(
                    "continuity chat",
                    rt.gateway.deps,
                    {
                        "offline": True,
                        "trace_id": tid,
                        "correlation_id": tid,
                        "session_id": "sess-c",
                        "tenant_id": "ten-c",
                    },
                )
                interesting = {
                    "input.text",
                    "routing.selected",
                    "model.completed",
                    "response.completed",
                }
                matched = [e for e in seen if e.event_type in interesting]
                self.assertGreaterEqual(len(matched), 4)
                for e in matched:
                    self.assertEqual(e.trace_id, tid)
                    self.assertEqual(e.correlation_id, tid)
                    self.assertEqual(e.tenant_id, "ten-c")
                    self.assertEqual(e.session_id, "sess-c")
            finally:
                unsub()

    def test_tool_trace_continuity(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            seen, unsub = _collect_events(rt.cognitive_runtime.bus)
            try:
                tid = "tool-trace-001"
                tr = TraceContext(
                    trace_id=tid,
                    correlation_id=tid,
                    tenant_id="ten-tool",
                    session_id="sess-tool",
                    role="GUEST",
                    runtime_mode="shadow",
                    source="test",
                )
                rt.gateway.deps["trace_context"] = tr
                with mock.patch(
                    "ssn.interfaces.handlers_tools.verify_owner",
                    return_value={
                        "master_key_score": 1.0,
                        "biometric_score": 0.0,
                        "behavior_score": 0.0,
                        "overall_score": 0.7,
                    },
                ), mock.patch(
                    "ssn.interfaces.handlers_tools.is_samson_verified",
                    return_value=True,
                ):
                    req = InterfaceRequest(
                        action="run_tool",
                        role="GUEST",
                        context={
                            "tool_name": "tools.list",
                            "args": {},
                            "trace_id": tid,
                            "correlation_id": tid,
                            "tenant_id": "ten-tool",
                            "session_id": "sess-tool",
                        },
                        meta={"master_key": "TEST"},
                    )
                    handle_run_tool(req, rt.gateway.deps)
                tool_events = [
                    e
                    for e in seen
                    if e.event_type in ("tool.proposed", "tool.started", "tool.completed", "tool.failed")
                ]
                self.assertGreaterEqual(len(tool_events), 1)
                for e in tool_events:
                    self.assertEqual(e.trace_id, tid)
                    self.assertEqual(e.correlation_id, tid)
            finally:
                unsub()

    def test_sense_tick_trace_continuity(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            seen, unsub = _collect_events(rt.cognitive_runtime.bus)
            try:
                tid = "sense-trace-001"
                with mock.patch(
                    "ssn.interfaces.handlers_sense_tick.verify_owner",
                    return_value={
                        "master_key_score": 1.0,
                        "biometric_score": 0.0,
                        "behavior_score": 0.0,
                        "overall_score": 0.7,
                    },
                ), mock.patch(
                    "ssn.interfaces.handlers_sense_tick.is_samson_verified",
                    return_value=True,
                ):
                    req = InterfaceRequest(
                        action="sense_tick",
                        role="GUEST",
                        context={
                            "master_key": "TEST",
                            "trace_id": tid,
                            "correlation_id": tid,
                            "tenant_id": "ten-sense",
                            "session_id": "sess-sense",
                            "events": [{"type": "motion_event", "ts": 1.0, "confidence": 0.6}],
                        },
                        meta={},
                    )
                    handle_sense_tick(req, rt.gateway.deps)
                sense_types = {
                    "sensor.observation",
                    "perception.completed",
                    "world.updated",
                }
                matched = [e for e in seen if e.event_type in sense_types]
                self.assertGreaterEqual(len(matched), 2)
                for e in matched:
                    self.assertEqual(e.trace_id, tid)
                    self.assertEqual(e.correlation_id, tid)
                    self.assertEqual(e.tenant_id, "ten-sense")
                    self.assertEqual(e.session_id, "sess-sense")
            finally:
                unsub()

    def test_extract_or_create_preserves_fields(self):
        tr = TraceContext.extract_or_create(
            context={
                "trace_id": "t-x",
                "correlation_id": "c-x",
                "tenant_id": "ten",
                "session_id": "sess",
            },
            deps={"cognitive_mode": "shadow"},
            role="GUEST",
            source="test",
        )
        self.assertEqual(tr.trace_id, "t-x")
        self.assertEqual(tr.correlation_id, "c-x")
        self.assertEqual(tr.tenant_id, "ten")
        self.assertEqual(tr.session_id, "sess")
        self.assertEqual(tr.role, "GUEST")
        self.assertEqual(tr.runtime_mode, "shadow")


class TestAsyncObservationLifecycle(unittest.TestCase):
    def test_zero_pending_after_repeated_async_emits(self):
        async def _run():
            cr = CognitiveRuntime.create()
            facade = IntegrationFacade.create(cognitive_runtime=cr, mode="shadow")
            tr = TraceContext(runtime_mode="shadow", trace_id="async-batch")
            for i in range(40):
                await facade.events.emit_async(
                    "input.text",
                    source="test",
                    payload={"i": i},
                    trace=tr,
                )
            await facade.drain()
            self.assertEqual(facade.pending_observation_tasks, 0)
            await facade.shutdown()
            self.assertEqual(facade.pending_observation_tasks, 0)

        asyncio.run(_run())

    def test_tracked_sync_emit_from_running_loop_then_drain(self):
        async def _run():
            cr = CognitiveRuntime.create()
            facade = IntegrationFacade.create(cognitive_runtime=cr, mode="shadow")
            tr = TraceContext(runtime_mode="shadow", trace_id="sync-in-loop")
            for i in range(20):
                facade.events.emit_sync(
                    "input.text",
                    source="test",
                    payload={"i": i},
                    trace=tr,
                )
            await facade.drain()
            self.assertEqual(facade.pending_observation_tasks, 0)
            await facade.shutdown()

        asyncio.run(_run())

    def test_delivery_errors_counted(self):
        async def _run():
            cr = CognitiveRuntime.create()
            facade = IntegrationFacade.create(cognitive_runtime=cr, mode="shadow")
            before = facade.metrics.event_delivery_errors

            async def fail_dispatch(event):
                raise RuntimeError("forced delivery failure")

            facade.events.bus.dispatch_inline = fail_dispatch  # type: ignore[method-assign]
            await facade.events.emit_async(
                "runtime.error",
                source="test",
                payload={"x": 1},
                trace=TraceContext(runtime_mode="shadow"),
            )
            self.assertEqual(facade.metrics.event_delivery_errors, before + 1)
            await facade.shutdown()

        asyncio.run(_run())


class TestShadowAndExperimentalSemantics(unittest.TestCase):
    def test_shadow_response_authoritative_no_extra_model(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            before = rt.integration.metrics.model_requests
            out = handle_user_message("shadow auth", rt.gateway.deps, {"offline": True})
            self.assertTrue(out.get("integration", {}).get("authoritative"))
            self.assertFalse(out.get("integration", {}).get("duplicate_model_call", True))
            self.assertEqual(rt.integration.metrics.model_requests, before)

    def test_cognitive_experimental_opt_in(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "legacy", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            out = handle_user_message("no exp", rt.gateway.deps, {"offline": True})
            self.assertNotIn("cognitive_experimental", out)
            self.assertNotIn("experimental", out)
        with mock.patch.dict(
            os.environ, {"SSN_COGNITIVE_MODE": "cognitive_experimental", "SSN_OFFLINE": "1"}
        ):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            out = handle_user_message("yes exp", rt.gateway.deps, {"offline": True})
            self.assertTrue(out.get("experimental"))
            self.assertIn("cognitive_experimental", out)


class TestOwnerControlUnchanged(unittest.TestCase):
    def test_guest_still_blocked_from_owner_tool_path(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            req = InterfaceRequest(
                action="run_tool",
                role="OWNER",  # claimed but unverified
                context={"tool_name": "tools.list", "args": {}},
                meta={},
            )
            resp = handle_run_tool(req, rt.gateway.deps)
            # Without master key, role resolves to GUEST — policy path unchanged
            self.assertEqual(resp.role, "GUEST")

    def test_sense_tick_still_policy_gated(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            req = InterfaceRequest(action="sense_tick", role="OWNER", context={}, meta={})
            resp = handle_sense_tick(req, rt.gateway.deps)
            self.assertEqual(resp.data.get("final_result"), "BLOCKED_BY_POLICY")


class TestProductScopeDocs(unittest.TestCase):
    def test_no_pulse_or_weza_in_core_architecture_docs(self):
        docs = [
            ROOT / "docs" / "SIONA_VISION.md",
            ROOT / "docs" / "SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md",
            ROOT / "docs" / "SIONA_PHASE_ROADMAP.md",
            ROOT / "docs" / "adr" / "0001-hybrid-runtime-integration.md",
            ROOT / "docs" / "PHASE_STATUS.md",
            ROOT / "docs" / "DEFERRED_CAPABILITIES.md",
            ROOT / "docs" / "HARDWARE_ROADMAP.md",
            ROOT / "docs" / "TECHNICAL_DEBT_REGISTER.md",
            ROOT / "docs" / "EXPERIMENT_LOG.md",
        ]
        pattern = re.compile(r"\b(Pulse|Weza AI|Weza)\b", re.IGNORECASE)
        for path in docs:
            if not path.exists():
                continue
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(
                pattern.search(text),
                f"Found Pulse/Weza reference in {path}",
            )


if __name__ == "__main__":
    unittest.main()
