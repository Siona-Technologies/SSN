"""
Phase 2 final gate — shared-deps trace isolation and async shutdown safety.
"""

from __future__ import annotations

import asyncio
import os
import re
import unittest
import warnings
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest import mock

os.environ.setdefault("SSN_OFFLINE", "1")

from ssn.cognition.loop import CognitiveRuntime
from ssn.integration.event_bridge import (
    EventBridge,
    EventBridgeShutdownInAsyncContextError,
    EventBridgeSyncInAsyncContextError,
)
from ssn.integration.facade import IntegrationFacade
from ssn.integration.trace_context import TraceContext
from ssn.interfaces.contracts import InterfaceRequest
from ssn.interfaces.front_door import handle_user_message
from ssn.interfaces.handlers_sense_tick import handle_sense_tick
from ssn.interfaces.handlers_tools import handle_run_tool
from ssn.runtime.runtime_builder import SSNRuntimeBuilder

ROOT = Path(__file__).resolve().parents[2]


def _collect_events(bus):
    seen = []

    async def _handler(event):
        seen.append(event)

    unsub = bus.subscribe(_handler, name="trace-isolation-collector")
    return seen, unsub


class TestSharedDepsNeverHoldTrace(unittest.TestCase):
    def test_no_trace_context_key_after_chat(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            deps = rt.gateway.deps
            self.assertNotIn("trace_context", deps)
            handle_user_message(
                "chat A",
                deps,
                {"offline": True, "trace_id": "chat-a", "session_id": "s1", "tenant_id": "t1"},
            )
            self.assertNotIn("trace_context", deps)
            handle_user_message(
                "chat B",
                deps,
                {"offline": True, "trace_id": "chat-b", "session_id": "s2", "tenant_id": "t2"},
            )
            self.assertNotIn("trace_context", deps)


class TestSequentialTraceIsolation(unittest.TestCase):
    def test_two_sequential_requests_different_traces_same_deps(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            deps = rt.gateway.deps
            seen, unsub = _collect_events(rt.cognitive_runtime.bus)
            try:
                out1 = handle_user_message(
                    "first",
                    deps,
                    {
                        "offline": True,
                        "trace_id": "seq-1",
                        "correlation_id": "seq-1",
                        "tenant_id": "ten-a",
                        "session_id": "sess-a",
                    },
                )
                out2 = handle_user_message(
                    "second",
                    deps,
                    {
                        "offline": True,
                        "trace_id": "seq-2",
                        "correlation_id": "seq-2",
                        "tenant_id": "ten-b",
                        "session_id": "sess-b",
                    },
                )
                self.assertEqual(out1.get("trace_id"), "seq-1")
                self.assertEqual(out2.get("trace_id"), "seq-2")
                e1 = [e for e in seen if e.trace_id == "seq-1"]
                e2 = [e for e in seen if e.trace_id == "seq-2"]
                self.assertGreaterEqual(len(e1), 1)
                self.assertGreaterEqual(len(e2), 1)
                for e in e1:
                    self.assertEqual(e.tenant_id, "ten-a")
                    self.assertEqual(e.session_id, "sess-a")
                for e in e2:
                    self.assertEqual(e.tenant_id, "ten-b")
                    self.assertEqual(e.session_id, "sess-b")
            finally:
                unsub()

    def test_tool_after_chat_does_not_inherit_unless_explicit(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            deps = rt.gateway.deps
            seen, unsub = _collect_events(rt.cognitive_runtime.bus)
            try:
                handle_user_message(
                    "chat first",
                    deps,
                    {"offline": True, "trace_id": "chat-only", "correlation_id": "chat-only"},
                )
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
                    # No chat trace in tool request
                    req = InterfaceRequest(
                        action="run_tool",
                        role="GUEST",
                        context={"tool_name": "tools.list", "args": {}},
                        meta={"master_key": "TEST"},
                    )
                    handle_run_tool(req, deps)
                tool_events = [
                    e
                    for e in seen
                    if e.event_type in ("tool.proposed", "tool.started", "tool.completed", "tool.failed")
                ]
                self.assertGreaterEqual(len(tool_events), 1)
                for e in tool_events:
                    self.assertNotEqual(e.trace_id, "chat-only")

                # Explicit inclusion does propagate
                n_before = len(seen)
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
                    req2 = InterfaceRequest(
                        action="run_tool",
                        role="GUEST",
                        context={
                            "tool_name": "tools.list",
                            "args": {},
                            "trace_id": "chat-only",
                            "correlation_id": "chat-only",
                        },
                        meta={"master_key": "TEST"},
                    )
                    handle_run_tool(req2, deps)
                tool2 = [
                    e
                    for e in seen[n_before:]
                    if e.event_type in ("tool.proposed", "tool.started", "tool.completed", "tool.failed")
                ]
                self.assertGreaterEqual(len(tool2), 1)
                for e in tool2:
                    self.assertEqual(e.trace_id, "chat-only")
            finally:
                unsub()

    def test_sense_tick_does_not_inherit_previous_trace(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            deps = rt.gateway.deps
            seen, unsub = _collect_events(rt.cognitive_runtime.bus)
            try:
                handle_user_message(
                    "prior",
                    deps,
                    {"offline": True, "trace_id": "prior-chat", "correlation_id": "prior-chat"},
                )
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
                            "events": [{"type": "motion_event", "ts": 1.0, "confidence": 0.6}],
                        },
                        meta={},
                    )
                    handle_sense_tick(req, deps)
                sense = [
                    e
                    for e in seen
                    if e.event_type in ("sensor.observation", "perception.completed", "world.updated")
                ]
                self.assertGreaterEqual(len(sense), 1)
                for e in sense:
                    self.assertNotEqual(e.trace_id, "prior-chat")
            finally:
                unsub()


class TestConcurrentTraceIsolation(unittest.TestCase):
    def test_two_concurrent_requests_same_deps(self):
        with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
            rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
            deps = rt.gateway.deps
            seen, unsub = _collect_events(rt.cognitive_runtime.bus)

            def _run(tid: str, tenant: str, session: str) -> str:
                out = handle_user_message(
                    f"msg-{tid}",
                    deps,
                    {
                        "offline": True,
                        "trace_id": tid,
                        "correlation_id": tid,
                        "tenant_id": tenant,
                        "session_id": session,
                    },
                )
                return str(out.get("trace_id"))

            try:
                with ThreadPoolExecutor(max_workers=2) as pool:
                    f1 = pool.submit(_run, "conc-1", "ten-1", "sess-1")
                    f2 = pool.submit(_run, "conc-2", "ten-2", "sess-2")
                    self.assertEqual(f1.result(), "conc-1")
                    self.assertEqual(f2.result(), "conc-2")
                for tid, tenant, session in (
                    ("conc-1", "ten-1", "sess-1"),
                    ("conc-2", "ten-2", "sess-2"),
                ):
                    matched = [e for e in seen if e.trace_id == tid]
                    self.assertGreaterEqual(len(matched), 1)
                    for e in matched:
                        self.assertEqual(e.tenant_id, tenant)
                        self.assertEqual(e.session_id, session)
                        self.assertEqual(e.correlation_id, tid)
            finally:
                unsub()


class TestExtractPrecedence(unittest.TestCase):
    def test_request_fields_win_over_contextvar(self):
        ambient = TraceContext(trace_id="ambient", correlation_id="ambient", runtime_mode="shadow")
        token = TraceContext.set_request_local(ambient)
        try:
            tr = TraceContext.extract_or_create(
                context={"trace_id": "request-wins", "correlation_id": "request-wins"},
                role="GUEST",
                runtime_mode="shadow",
            )
            self.assertEqual(tr.trace_id, "request-wins")
        finally:
            TraceContext.reset_request_local(token)

    def test_explicit_trace_wins(self):
        explicit = TraceContext(trace_id="explicit", correlation_id="explicit")
        tr = TraceContext.extract_or_create(
            context={"trace_id": "ignored"},
            trace=explicit,
        )
        self.assertEqual(tr.trace_id, "explicit")

    def test_deps_trace_context_ignored(self):
        planted = TraceContext(trace_id="planted-deps", correlation_id="planted-deps")
        tr = TraceContext.extract_or_create(
            context={},
            deps={"trace_context": planted, "cognitive_mode": "shadow"},
            role="GUEST",
            runtime_mode="shadow",
        )
        self.assertNotEqual(tr.trace_id, "planted-deps")


class TestAsyncShutdownLifecycle(unittest.TestCase):
    def test_async_shutdown_drains_all(self):
        async def _run():
            cr = CognitiveRuntime.create()
            facade = IntegrationFacade.create(cognitive_runtime=cr, mode="shadow")
            tr = TraceContext(runtime_mode="shadow", trace_id="shut-async")
            for i in range(30):
                facade.events.emit_sync(
                    "input.text",
                    source="test",
                    payload={"i": i},
                    trace=tr,
                )
            await facade.shutdown()
            self.assertEqual(facade.pending_observation_tasks, 0)
            before = facade.metrics.event_delivery_errors
            out = await facade.events.emit_async(
                "input.text",
                source="test",
                payload={"after": True},
                trace=tr,
            )
            self.assertIsNone(out)
            self.assertEqual(facade.metrics.event_delivery_errors, before + 1)

        asyncio.run(_run())

    def test_shutdown_sync_outside_loop(self):
        cr = CognitiveRuntime.create()
        facade = IntegrationFacade.create(cognitive_runtime=cr, mode="shadow")
        facade.shutdown_sync()
        self.assertEqual(facade.pending_observation_tasks, 0)

    def test_shutdown_sync_inside_loop_raises(self):
        async def _run():
            cr = CognitiveRuntime.create()
            facade = IntegrationFacade.create(cognitive_runtime=cr, mode="shadow")
            with self.assertRaises(EventBridgeShutdownInAsyncContextError) as ctx:
                facade.shutdown_sync()
            self.assertIn("await", str(ctx.exception).lower())
            await facade.shutdown()

        asyncio.run(_run())

    def test_runtime_shutdown_sync_inside_loop_raises(self):
        async def _run():
            with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
                rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
                with self.assertRaises(EventBridgeShutdownInAsyncContextError):
                    rt.shutdown_sync()
                await rt.shutdown()

        asyncio.run(_run())

    def test_shutdown_never_waits_on_itself(self):
        async def _run():
            cr = CognitiveRuntime.create()
            bridge = EventBridge(cr.bus, max_pending_tasks=8)
            # Manually plant current-task-like wait would deadlock if drain included self;
            # calling shutdown from within an async task must complete.
            await bridge.shutdown(timeout_s=1.0)
            self.assertTrue(bridge._closed)

        asyncio.run(_run())

    def test_pending_saturation_no_unawaited_coroutine_warning(self):
        async def _run():
            from ssn.integration.observability import IntegrationMetrics

            cr = CognitiveRuntime.create()
            metrics = IntegrationMetrics()
            bridge = EventBridge(cr.bus, metrics=metrics, max_pending_tasks=2)
            tr = TraceContext(runtime_mode="shadow")

            async def _slow(_event):
                await asyncio.sleep(0.25)

            bridge.bus.dispatch_inline = _slow  # type: ignore[method-assign]

            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                # Fill registry (emit_sync catches capacity errors and records metrics)
                self.assertIsNotNone(
                    bridge.emit_sync("input.text", source="t", payload={"i": 0}, trace=tr)
                )
                self.assertIsNotNone(
                    bridge.emit_sync("input.text", source="t", payload={"i": 1}, trace=tr)
                )
                before = metrics.event_delivery_errors
                # Saturation: factory must not leave an unawaited coroutine
                out = bridge.emit_sync("input.text", source="t", payload={"i": 2}, trace=tr)
                self.assertIsNone(out)
                self.assertEqual(metrics.event_delivery_errors, before + 1)
                await asyncio.sleep(0.05)
            msgs = [str(w.message) for w in caught]
            self.assertFalse(
                any("never awaited" in m for m in msgs),
                msgs,
            )
            await bridge.drain()
            await bridge.shutdown()

        asyncio.run(_run())

    def test_no_observation_task_after_shutdown(self):
        async def _run():
            with mock.patch.dict(os.environ, {"SSN_COGNITIVE_MODE": "shadow", "SSN_OFFLINE": "1"}):
                rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
                for i in range(15):
                    handle_user_message(f"m{i}", rt.gateway.deps, {"offline": True})
                await rt.shutdown()
                self.assertEqual(rt.integration.pending_observation_tasks, 0)

        asyncio.run(_run())


class TestAssistantTerminologyDocs(unittest.TestCase):
    def test_core_arch_docs_have_no_jarvis_pulse_weza(self):
        docs = [
            ROOT / "docs" / "SIONA_VISION.md",
            ROOT / "docs" / "SIONA_NEUROMORPHIC_ARCHITECTURE_V1.md",
            ROOT / "docs" / "SIONA_PHASE_ROADMAP.md",
            ROOT / "docs" / "adr" / "0001-hybrid-runtime-integration.md",
            ROOT / "docs" / "PHASE_STATUS.md",
        ]
        banned = re.compile(r"\b(Jarvis|Pulse|Weza AI|Weza)\b", re.IGNORECASE)
        for path in docs:
            text = path.read_text(encoding="utf-8")
            self.assertIsNone(banned.search(text), f"banned name in {path}")
        vision = (ROOT / "docs" / "SIONA_VISION.md").read_text(encoding="utf-8")
        self.assertIn("future user-facing assistant embodiment", vision)
        self.assertIn("SIBONA", vision)


if __name__ == "__main__":
    unittest.main()
