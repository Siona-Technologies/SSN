"""
Phase 1 hardening tests — backpressure, queue leak, isolation, timeout/fallback.
"""

from __future__ import annotations

import asyncio
import os
import time
import unittest

os.environ.setdefault("SSN_OFFLINE", "1")

from ssn.cognition.event_bus import AsyncEventBus, match_event_type
from ssn.cognition.events import CognitiveEvent, EventPriority
from ssn.cognition.loop import (
    CognitiveLoop,
    CognitiveLoopSyncInAsyncContextError,
    CognitiveRuntime,
)
from ssn.cognition.model_gateway import (
    CancelToken,
    DeterministicModelProvider,
    FailingModelProvider,
    LegacyLLMProviderAdapter,
    MalformedModelProvider,
    ModelGateway,
    ModelRequest,
    SlowModelProvider,
    UnhealthyModelProvider,
)
from ssn.cognition.workspace import (
    GlobalCognitiveWorkspace,
    GoalItem,
    WorkspaceRegistry,
    normalize_session_id,
)
from ssn.core.llm_providers import HttpLLMProvider as CoreHttpLLMProvider


class TestBackpressurePolicy(unittest.TestCase):
    def test_background_cannot_evict_critical(self):
        bus = AsyncEventBus(max_queue_size=1, drop_on_full=True)
        crit = CognitiveEvent(
            event_type="crit", source="t", priority=EventPriority.CRITICAL, event_id="c1"
        )
        bg = CognitiveEvent(
            event_type="bg", source="t", priority=EventPriority.BACKGROUND, event_id="b1"
        )
        self.assertTrue(bus.publish_nowait(crit))
        self.assertFalse(bus.publish_nowait(bg))
        self.assertEqual(bus.queued_event_ids(), ["c1"])
        self.assertEqual(bus.metrics.incoming_rejected, 1)
        self.assertEqual(bus.metrics.queued_evicted, 0)

    def test_critical_can_evict_background(self):
        bus = AsyncEventBus(max_queue_size=1, drop_on_full=True)
        bg = CognitiveEvent(
            event_type="bg", source="t", priority=EventPriority.BACKGROUND, event_id="b1"
        )
        crit = CognitiveEvent(
            event_type="crit", source="t", priority=EventPriority.CRITICAL, event_id="c1"
        )
        self.assertTrue(bus.publish_nowait(bg))
        self.assertTrue(bus.publish_nowait(crit))
        self.assertEqual(bus.queued_event_ids(), ["c1"])
        self.assertEqual(bus.metrics.queued_evicted, 1)
        self.assertEqual(bus.metrics.incoming_rejected, 0)

    def test_equal_priority_rejects_incoming(self):
        bus = AsyncEventBus(max_queue_size=1, drop_on_full=True)
        a = CognitiveEvent(
            event_type="a", source="t", priority=EventPriority.NORMAL, event_id="a1"
        )
        b = CognitiveEvent(
            event_type="b", source="t", priority=EventPriority.NORMAL, event_id="b1"
        )
        self.assertTrue(bus.publish_nowait(a))
        self.assertFalse(bus.publish_nowait(b))
        self.assertEqual(bus.queued_event_ids(), ["a1"])
        self.assertEqual(bus.metrics.incoming_rejected, 1)

    def test_fifo_within_priority(self):
        bus = AsyncEventBus(max_queue_size=3, drop_on_full=True)
        ids = []
        for i in range(3):
            eid = f"n{i}"
            ids.append(eid)
            self.assertTrue(
                bus.publish_nowait(
                    CognitiveEvent(
                        event_type="n",
                        source="t",
                        priority=EventPriority.NORMAL,
                        event_id=eid,
                    )
                )
            )
        self.assertEqual(
            bus.queued_event_ids(EventPriority.NORMAL),
            ids,
        )

    def test_expired_rejected_metric(self):
        bus = AsyncEventBus(max_queue_size=4)
        ev = CognitiveEvent(
            event_type="old",
            source="t",
            expires_at=time.time() - 1.0,
            ttl_ms=1,
        )
        self.assertFalse(bus.publish_nowait(ev))
        self.assertEqual(bus.metrics.expired_rejected, 1)


class TestEventFilters(unittest.TestCase):
    def test_exact_and_prefix(self):
        self.assertTrue(match_event_type("sensor.imu", "sensor.imu"))
        self.assertFalse(match_event_type("sensor.imu", "sensor.imu.extra"))
        self.assertFalse(match_event_type("sensor.imu", "sensor.cam"))
        self.assertTrue(match_event_type("sensor.*", "sensor.imu"))
        self.assertTrue(match_event_type("sensor.*", "sensor.cam"))
        self.assertFalse(match_event_type("sensor.*", "audio.chunk"))
        # Bare "sensor." is exact-only (no undocumented prefix match)
        self.assertFalse(match_event_type("sensor.", "sensor.imu"))
        self.assertTrue(match_event_type("sensor.", "sensor."))

    def test_list_patterns(self):
        bus = AsyncEventBus()
        seen = []

        def handler(ev):
            seen.append(ev.event_type)

        bus.subscribe(handler, event_type=["sensor.imu", "audio.*"])

        async def _run():
            await bus.dispatch_inline(
                CognitiveEvent(event_type="sensor.imu", source="t")
            )
            await bus.dispatch_inline(
                CognitiveEvent(event_type="sensor.cam", source="t")
            )
            await bus.dispatch_inline(
                CognitiveEvent(event_type="audio.chunk", source="t")
            )

        asyncio.run(_run())
        self.assertEqual(seen, ["sensor.imu", "audio.chunk"])


class TestQueueLeak(unittest.TestCase):
    def test_queue_depth_zero_after_one_request(self):
        loop = CognitiveLoop(CognitiveRuntime.create())
        seen = []
        loop.rt.bus.subscribe(lambda ev: seen.append(ev.event_id), event_type="input.text")
        out = loop.process_text("leak check", role="GUEST", session_id="s1")
        self.assertEqual(loop.rt.bus.queue_depth, 0)
        self.assertEqual(out["metadata"]["queue_depth"], 0)
        self.assertEqual(len(seen), 1)
        self.assertEqual(loop.rt.bus.metrics.published, 1)
        self.assertEqual(loop.rt.bus.metrics.delivered, 1)

    def test_queue_depth_zero_after_1500_requests(self):
        loop = CognitiveLoop(CognitiveRuntime.create())
        # Optional no-op subscriber so deliver metrics stay consistent if desired
        loop.rt.bus.subscribe(lambda _ev: None, event_type="input.text")
        published_before = loop.rt.bus.metrics.published
        delivered_before = loop.rt.bus.metrics.delivered
        for i in range(1500):
            loop.process_text(f"msg-{i}", role="GUEST", session_id="bulk")
            self.assertEqual(loop.rt.bus.queue_depth, 0)
        self.assertEqual(loop.rt.bus.queue_depth, 0)
        self.assertEqual(loop.rt.bus.metrics.published, published_before + 1500)
        self.assertEqual(loop.rt.bus.metrics.delivered, delivered_before + 1500)

    def test_subscribers_receive_inline_events(self):
        async def _run():
            rt = CognitiveRuntime.create()
            loop = CognitiveLoop(rt)
            seen = []

            async def handler(ev):
                seen.append(ev.payload.get("text"))

            rt.bus.subscribe(handler, event_type="input.text")
            await loop.process_text_async("hello-sub", session_id="s")
            self.assertEqual(rt.bus.queue_depth, 0)
            self.assertEqual(seen, ["hello-sub"])

        asyncio.run(_run())


class TestTenantSessionIsolation(unittest.TestCase):
    def test_empty_session_normalized(self):
        self.assertEqual(normalize_session_id(""), "_anon")
        self.assertEqual(normalize_session_id("  "), "_anon")
        self.assertEqual(normalize_session_id(None), "_anon")

    def test_cross_tenant_isolation(self):
        reg = WorkspaceRegistry(max_workspaces=16)
        a = reg.get("tenantA", "s1")
        b = reg.get("tenantB", "s1")
        a.update_context({"secret": "A-only", "last_user_text": "tenant A text"})
        a.add_memory_ref("mem:A")
        a.upsert_goal(GoalItem(goal_id="gA", description="A goal"))
        snap_b = b.snapshot().to_dict()
        self.assertNotIn("secret", snap_b["working_context_keys"])
        self.assertNotIn("last_user_text", snap_b["working_context_keys"])
        self.assertEqual(snap_b["memory_refs"], [])
        self.assertEqual(snap_b["goals"], [])
        self.assertEqual(snap_b["tenant_id"], "tenantB")
        snap_a = a.snapshot().to_dict()
        self.assertIn("secret", snap_a["working_context_keys"])
        self.assertEqual(snap_a["tenant_id"], "tenantA")

    def test_cross_session_isolation(self):
        loop = CognitiveLoop(CognitiveRuntime.create())
        loop.process_text("alpha", tenant_id="t1", session_id="sess-1")
        loop.process_text("beta", tenant_id="t1", session_id="sess-2")
        ws1 = loop.rt.workspaces.get("t1", "sess-1")
        ws2 = loop.rt.workspaces.get("t1", "sess-2")
        self.assertEqual(ws1._context.get("last_user_text"), "alpha")
        self.assertEqual(ws2._context.get("last_user_text"), "beta")
        self.assertNotEqual(ws1.scope_key, ws2.scope_key)

    def test_registry_lru_bound(self):
        reg = WorkspaceRegistry(max_workspaces=2, ttl_s=None)
        reg.get("t", "1")
        reg.get("t", "2")
        reg.get("t", "3")
        self.assertEqual(len(reg), 2)
        self.assertGreaterEqual(reg.evictions, 1)
        self.assertNotIn("t::1", reg.keys())


class TestAttentionInvalidation(unittest.TestCase):
    def test_critical_after_decision_becomes_selected(self):
        ws = GlobalCognitiveWorkspace()
        low = CognitiveEvent(
            event_type="low",
            source="t",
            priority=EventPriority.LOW,
            confidence=1.0,
            event_id="low1",
        )
        ws.ingest_event(low, salience=0.9)
        d1 = ws.select_attention()
        self.assertEqual(d1.selected.event_id, "low1")
        crit = CognitiveEvent(
            event_type="crit",
            source="t",
            priority=EventPriority.CRITICAL,
            requires_attention=True,
            event_id="crit1",
        )
        ws.ingest_event(crit, salience=0.1)
        # Snapshot must not reuse stale decision
        snap = ws.snapshot()
        self.assertEqual(snap.attention["selected_event_id"], "crit1")


class TestPortableExpiry(unittest.TestCase):
    def test_ttl_survives_transport_reconstruction(self):
        now = time.time()
        ev = CognitiveEvent(
            event_type="x",
            source="t",
            ttl_ms=5000,
            timestamp=now,
            expires_at=now + 5.0,
        )
        wire = ev.to_dict()
        # Simulate another process: fake a different monotonic clock on wire
        wire["monotonic_timestamp"] = 1.0
        restored = CognitiveEvent.from_dict(wire)
        self.assertFalse(restored.is_expired(now_wall=now + 1.0))
        self.assertTrue(restored.is_expired(now_wall=now + 6.0))
        # Receipt monotonic was refreshed (not the wire value)
        self.assertNotEqual(restored.monotonic_timestamp, 1.0)


class TestModelTimeoutFallback(unittest.TestCase):
    def test_timeout_falls_through(self):
        gw = ModelGateway(
            providers=[SlowModelProvider(sleep_s=1.0), DeterministicModelProvider()]
        )
        req = ModelRequest.from_prompt("timeout please")
        req.timeout_s = 0.1
        resp = gw.complete(req)
        self.assertTrue(resp.healthy)
        self.assertTrue(resp.fallback_used)
        self.assertGreaterEqual(gw.metrics.model_timeouts, 1)
        self.assertIn("deterministic", (resp.provider or "").lower())

    def test_cancellation(self):
        token = CancelToken()
        token.cancel()
        gw = ModelGateway(providers=[DeterministicModelProvider()])
        req = ModelRequest.from_prompt("nope")
        req.cancel_token = token
        resp = gw.complete(req)
        self.assertEqual(resp.finish_reason, "cancelled")
        self.assertFalse(resp.healthy)

    def test_unhealthy_and_malformed_fallback(self):
        gw = ModelGateway(
            providers=[
                UnhealthyModelProvider(),
                MalformedModelProvider(mode="empty"),
                DeterministicModelProvider(),
            ]
        )
        resp = gw.complete(ModelRequest.from_prompt("need good"))
        self.assertTrue(resp.healthy)
        self.assertTrue(resp.fallback_used)
        self.assertGreaterEqual(gw.metrics.model_fallbacks, 1)

    def test_malformed_json_fallback(self):
        gw = ModelGateway(
            providers=[
                MalformedModelProvider(mode="bad_json"),
                DeterministicModelProvider(),
            ]
        )
        req = ModelRequest.from_prompt("json please")
        req.response_format = "json"
        resp = gw.complete(req)
        self.assertTrue(resp.healthy)
        self.assertIsInstance(resp.structured, dict)

    def test_all_providers_fail(self):
        gw = ModelGateway(providers=[FailingModelProvider(), UnhealthyModelProvider()])
        resp = gw.complete(ModelRequest.from_prompt("x"))
        self.assertFalse(resp.healthy)
        self.assertEqual(resp.finish_reason, "error")

    def test_http_stub_not_healthy_in_gateway(self):
        # Unconfigured HttpLLMProvider returns stub with fallback_reason
        adapter = LegacyLLMProviderAdapter(CoreHttpLLMProvider(base_url=""))
        gw = ModelGateway(providers=[adapter, DeterministicModelProvider()])
        resp = gw.complete(ModelRequest.from_prompt("hi"))
        self.assertTrue(resp.healthy)
        self.assertTrue(resp.fallback_used)
        self.assertEqual(resp.provider, DeterministicModelProvider.name)

    def test_exception_fallback(self):
        gw = ModelGateway(
            providers=[FailingModelProvider(), DeterministicModelProvider()]
        )
        resp = gw.complete(ModelRequest.from_prompt("hi"))
        self.assertTrue(resp.fallback_used)
        self.assertTrue(resp.healthy)


class TestSyncAsyncApi(unittest.TestCase):
    def test_sync_works_without_running_loop(self):
        loop = CognitiveLoop(CognitiveRuntime.create())
        out = loop.process_text("sync ok")
        self.assertIn("reply", out)

    def test_sync_raises_inside_running_loop(self):
        async def _run():
            loop = CognitiveLoop(CognitiveRuntime.create())
            with self.assertRaises(CognitiveLoopSyncInAsyncContextError):
                loop.process_text("should fail")
            # Async path still works
            result = await loop.process_text_async("async ok")
            self.assertTrue(result.reply)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
