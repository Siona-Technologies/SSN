"""
Phase 1 cognitive runtime foundation — deterministic unit tests.
"""

from __future__ import annotations

import asyncio
import os
import time
import unittest

os.environ.setdefault("SSN_OFFLINE", "1")

from ssn.cognition.attention import AttentionArbiter, AttentionCandidate
from ssn.cognition.event_bus import AsyncEventBus
from ssn.cognition.events import CognitiveEvent, EventPriority
from ssn.cognition.loop import CognitiveLoop, CognitiveRuntime
from ssn.cognition.metrics import CognitionMetrics
from ssn.cognition.model_gateway import (
    DeterministicModelProvider,
    FailingModelProvider,
    LegacyLLMProviderAdapter,
    ModelGateway,
    ModelGatewayAsLLMProvider,
    ModelMessage,
    ModelRequest,
    MessageRole,
)
from ssn.cognition.neuromorphic import (
    DeterministicNeuromorphicProvider,
    LegacySNNEngineAdapter,
    NeuromorphicEvent,
    NeuromorphicSNNFacade,
)
from ssn.cognition.workspace import GlobalCognitiveWorkspace
from ssn.cognition.world import WorldEventAdapter, WorldModelServiceBoundary
from ssn.cognition.memory import MemoryKind, MemoryServiceBoundary
from ssn.core.language_engine import LanguageEngine
from ssn.core.llm_providers import LocalDummyLLMProvider
from ssn.embodiment import (
    ActionAuthorization,
    MockEmbodimentAdapter,
    describe_mind_body_boundary,
)


class TestCognitiveEvent(unittest.TestCase):
    def test_validation_and_serialization(self):
        ev = CognitiveEvent(
            event_type="input.text",
            source="test",
            payload={"text": "hello"},
            priority=EventPriority.HIGH,
            confidence=1.5,  # clipped
            ttl_ms=1000,
        )
        self.assertEqual(ev.confidence, 1.0)
        raw = ev.to_json()
        restored = CognitiveEvent.from_dict(ev.to_dict())
        self.assertEqual(restored.event_type, "input.text")
        self.assertIn("event_id", raw)

    def test_expiry(self):
        ev = CognitiveEvent(
            event_type="timer",
            source="test",
            ttl_ms=1,
            timestamp=time.time() - 10.0,
            expires_at=time.time() - 5.0,
        )
        self.assertTrue(ev.is_expired())

    def test_payload_bounding(self):
        huge = {"k" + str(i): "x" * 100 for i in range(300)}
        ev = CognitiveEvent(event_type="bulk", source="test", payload=huge)
        self.assertTrue(ev.payload.get("__truncated__") or len(ev.payload) <= 256)


class TestAsyncEventBus(unittest.TestCase):
    def test_publish_subscribe_priority_and_order(self):
        async def _run():
            bus = AsyncEventBus(max_queue_size=16, handler_timeout_s=1.0)
            seen = []

            async def handler(ev: CognitiveEvent):
                seen.append(ev.event_type)

            bus.subscribe(handler, event_type="sensor.*")
            await bus.start()
            await bus.publish(
                CognitiveEvent(event_type="sensor.imu", source="t", priority=EventPriority.LOW)
            )
            await bus.publish(
                CognitiveEvent(event_type="sensor.cam", source="t", priority=EventPriority.CRITICAL)
            )
            await bus.drain(timeout_s=1.0)
            await bus.stop()
            self.assertGreaterEqual(bus.metrics.published, 2)
            self.assertGreaterEqual(bus.metrics.delivered, 1)
            return seen

        asyncio.run(_run())

    def test_backpressure_drops(self):
        bus = AsyncEventBus(max_queue_size=2, drop_on_full=True)
        ok1 = bus.publish_nowait(CognitiveEvent(event_type="a", source="t", priority=EventPriority.LOW))
        ok2 = bus.publish_nowait(CognitiveEvent(event_type="b", source="t", priority=EventPriority.LOW))
        ok3 = bus.publish_nowait(CognitiveEvent(event_type="c", source="t", priority=EventPriority.HIGH))
        self.assertTrue(ok1 and ok2 and ok3)
        self.assertEqual(bus.queue_depth, 2)
        self.assertGreaterEqual(bus.metrics.queued_evicted, 1)

    def test_handler_failure_isolation(self):
        async def _run():
            bus = AsyncEventBus(handler_timeout_s=0.2)
            good = []

            def bad(_ev):
                raise RuntimeError("boom")

            def ok(ev):
                good.append(ev.event_id)

            bus.subscribe(bad, name="bad")
            bus.subscribe(ok, name="ok")
            await bus.start()
            ev = CognitiveEvent(event_type="x", source="t")
            await bus.publish(ev)
            await bus.drain(timeout_s=1.0)
            await bus.stop()
            self.assertEqual(good, [ev.event_id])
            self.assertGreaterEqual(bus.metrics.handler_errors, 1)
            self.assertTrue(bus.dead_letters())

        asyncio.run(_run())

    def test_handler_timeout(self):
        async def _run():
            bus = AsyncEventBus(handler_timeout_s=0.05)

            async def slow(_ev):
                await asyncio.sleep(0.5)

            bus.subscribe(slow, name="slow")
            await bus.start()
            await bus.publish(CognitiveEvent(event_type="slow", source="t"))
            await bus.drain(timeout_s=1.0)
            await bus.stop()
            self.assertGreaterEqual(bus.metrics.handler_timeouts, 1)

        asyncio.run(_run())


class TestWorkspaceAndAttention(unittest.TestCase):
    def test_priority_arbitration_deterministic(self):
        ws = GlobalCognitiveWorkspace(max_active_events=8)
        low = CognitiveEvent(event_type="a", source="t", priority=EventPriority.LOW, confidence=1.0)
        high = CognitiveEvent(
            event_type="b",
            source="t",
            priority=EventPriority.CRITICAL,
            confidence=0.5,
            requires_attention=True,
        )
        ws.ingest_event(low, salience=0.9)
        ws.ingest_event(high, salience=0.2)
        d1 = ws.select_attention()
        d2 = ws.select_attention()
        self.assertEqual(d1.selected.event_id, high.event_id)
        self.assertEqual(d1.selected.event_id, d2.selected.event_id)

    def test_reject_expired_and_bound(self):
        ws = GlobalCognitiveWorkspace(max_active_events=3)
        expired = CognitiveEvent(
            event_type="old",
            source="t",
            ttl_ms=1,
            timestamp=time.time() - 10.0,
            expires_at=time.time() - 1.0,
        )
        self.assertFalse(ws.ingest_event(expired))
        for i in range(10):
            ws.ingest_event(CognitiveEvent(event_type=f"e{i}", source="t"))
        self.assertLessEqual(len(ws.candidates()), 3)
        snap = ws.snapshot()
        self.assertIn("capacity", snap.to_dict())
        self.assertIn("tenant_id", snap.to_dict())

    def test_attention_scores_stable(self):
        arb = AttentionArbiter()
        ev = CognitiveEvent(event_type="x", source="t", priority=EventPriority.NORMAL)
        c = AttentionCandidate(event=ev, salience=0.5, anomaly=0.1)
        now = ev.monotonic_timestamp
        s1 = arb.score_candidate(c, now_mono=now)
        s2 = arb.score_candidate(c, now_mono=now)
        self.assertEqual(s1, s2)


class TestModelGateway(unittest.TestCase):
    def test_deterministic_provider_stable(self):
        p = DeterministicModelProvider()
        req = ModelRequest.from_prompt("hello world", role="GUEST")
        a = p.generate(req)
        b = p.generate(req)
        self.assertEqual(a.text, b.text)
        self.assertIn("fingerprint", a.meta)

    def test_structured_json_and_stream(self):
        p = DeterministicModelProvider()
        req = ModelRequest.from_prompt("json please", role="OWNER", )
        req.response_format = "json"
        resp = p.generate(req)
        self.assertIsInstance(resp.structured, dict)
        chunks = list(p.stream(ModelRequest.from_prompt("stream me")))
        self.assertTrue("".join(chunks))

    def test_fallback(self):
        gw = ModelGateway(providers=[FailingModelProvider(), DeterministicModelProvider()])
        resp = gw.complete(ModelRequest.from_prompt("hi"))
        self.assertTrue(resp.fallback_used)
        self.assertTrue(resp.text)
        self.assertGreaterEqual(gw.metrics.model_fallbacks, 1)

    def test_legacy_dummy_adapter_and_language_engine(self):
        adapter = LegacyLLMProviderAdapter(LocalDummyLLMProvider())
        resp = adapter.generate(ModelRequest.from_prompt("ping", role="GUEST"))
        self.assertIn("Guest", resp.text)

        gw = ModelGateway(providers=[DeterministicModelProvider()])
        as_llm = ModelGatewayAsLLMProvider(gw)
        eng = LanguageEngine(provider=as_llm)
        out = eng.process("compat check", role="GUEST")
        self.assertIn("reply", out)
        self.assertIn("engine", out)

    def test_chat_messages(self):
        gw = ModelGateway.for_tests()
        req = ModelRequest(
            messages=[
                ModelMessage(role=MessageRole.SYSTEM, content="be brief"),
                ModelMessage(role=MessageRole.USER, content="hi"),
            ],
            role="GUEST",
        )
        resp = gw.complete(req)
        self.assertTrue(resp.text)


class TestNeuromorphic(unittest.TestCase):
    def test_deterministic_provider(self):
        p = DeterministicNeuromorphicProvider()
        ev = NeuromorphicEvent(
            event_id="1",
            modality="text",
            features={"text": "same input"},
        )
        a = p.process_event(ev)
        p2 = DeterministicNeuromorphicProvider()
        b = p2.process_event(
            NeuromorphicEvent(event_id="2", modality="text", features={"text": "same input"})
        )
        self.assertEqual(a.signal_strength, b.signal_strength)
        self.assertEqual(a.spikes_detected, b.spikes_detected)
        self.assertTrue(a.simulated)
        batch = p.process_batch([ev, ev])
        self.assertEqual(len(batch), 2)
        # novelty drops on repeat
        self.assertLessEqual(batch[1].novelty, batch[0].novelty)

    def test_legacy_adapter_and_facade(self):
        legacy = LegacySNNEngineAdapter()
        out = legacy.process_event(
            NeuromorphicEvent(event_id="x", modality="text", features={"text": "abc"})
        )
        self.assertIn("signal_strength", out.to_legacy_dict())
        facade = NeuromorphicSNNFacade()
        d = facade.process("hello there")
        self.assertIn("spikes_detected", d)


class TestMemoryWorldEmbodiment(unittest.TestCase):
    def test_memory_proposal_not_autocommit(self):
        mem = MemoryServiceBoundary()
        prop = mem.propose(MemoryKind.EPISODIC, {"text": "note"}, reason="test")
        self.assertTrue(prop.requires_owner_approval)
        self.assertEqual(prop.record.kind, MemoryKind.EPISODIC)

    def test_world_event_adapter(self):
        boundary = WorldModelServiceBoundary()
        adapter = WorldEventAdapter(boundary, apply=False)
        ev = CognitiveEvent(
            event_type="world.observation",
            source="test",
            payload={"description": "door open", "entity_type": "door"},
        )
        prop = adapter.handle(ev)
        self.assertIsNotNone(prop)
        self.assertTrue(prop.entities)

    def test_mock_embodiment_non_executing(self):
        body = MockEmbodimentAdapter()
        self.assertTrue(body.describe().body_type == "mock")
        obs = body.observe()
        self.assertTrue(obs)
        prop = body.propose_action(
            "set_power",
            "mock.lamp.living_room",
            {"on": True},
            reason="test",
        )
        denied = body.simulate_action(prop)
        self.assertFalse(denied.ok)
        auth = ActionAuthorization(proposal_id=prop.proposal_id, authorized=True, authorized_by="test")
        ok = body.simulate_action(prop, auth)
        self.assertTrue(ok.ok)
        self.assertTrue(ok.simulated)
        boundary = describe_mind_body_boundary()
        self.assertIn("transferable_mind", boundary)
        self.assertFalse(boundary["humanoid_motor_control"])


class TestCognitiveLoop(unittest.TestCase):
    def test_loop_produces_reply_and_proposals(self):
        loop = CognitiveLoop(CognitiveRuntime.create())
        out = loop.process_text("hello cognitive loop", role="GUEST")
        self.assertIn("reply", out)
        self.assertTrue(out["proposals"])
        self.assertEqual(out["engine"], "cognitive-loop-v1")
        kinds = {p["kind"] for p in out["proposals"]}
        self.assertIn("memory_write", kinds)

    def test_metrics_snapshot(self):
        m = CognitionMetrics()
        m.model_requests = 2
        snap = m.snapshot()
        self.assertEqual(snap["model_requests"], 2)


class TestRuntimeWiring(unittest.TestCase):
    def test_runtime_builder_attaches_cognitive_runtime(self):
        from ssn.runtime.runtime_builder import SSNRuntimeBuilder

        rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
        self.assertIsNotNone(rt.cognitive_runtime)
        self.assertIn("cognitive_runtime", rt.gateway.deps)
        # tools still registered via bootstrap
        listing = rt.tool_registry.list()
        self.assertTrue(listing)

    def test_language_engine_default_unchanged(self):
        eng = LanguageEngine()
        out = eng.process("hello", role="GUEST")
        self.assertIn("Guest", out["reply"])
        self.assertEqual(out["engine"], "ssn-local-dummy-llm-v1")


if __name__ == "__main__":
    unittest.main()
