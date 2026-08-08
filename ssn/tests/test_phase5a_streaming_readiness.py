"""EXP-5-001 Phase 5A streaming neuromorphic readiness (model-free)."""

from __future__ import annotations

import hashlib
import json
import math
import unittest
from pathlib import Path

from ssn.cognition.neuromorphic.contracts import NeuromorphicEvent
from ssn.cognition.neuromorphic.phase5a_streaming_contract import (
    RESERVED_PROVIDER_ID,
    STREAMING_MODALITY,
    StreamingLifecycleError,
    StreamingLifecycleTracker,
    load_streaming_contract,
    validate_streaming_step_event,
)

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "config" / "phase5a_streaming_neuromorphic_contract.json"
EVIDENCE = ROOT / "docs" / "evidence" / "EXP-5-001_STREAMING_NEUROMORPHIC_READINESS.json"
READINESS_DOC = ROOT / "docs" / "SIONA_PHASE_5A_STREAMING_READINESS.md"
PHASE4_ACCEPTANCE = ROOT / "docs" / "evidence" / "PHASE_4_ACCEPTANCE.json"
PHASE5_PLAN = ROOT / "docs" / "evidence" / "PHASE_5_PLANNING_ACCEPTANCE.json"
ADR4 = ROOT / "docs" / "adr" / "0004-learned-neuromorphic-backend-strategy.md"
ADR5 = ROOT / "docs" / "adr" / "0005-stateful-streaming-neuromorphic-strategy.md"
STATUS = ROOT / "docs" / "PHASE_STATUS.md"
ROADMAP = ROOT / "docs" / "SIONA_PHASE_ROADMAP.md"
ARTIFACT = ROOT / "artifacts" / "neuromorphic" / "phase4b-lif-final-membrane-v1.json"
REQUIREMENTS = ROOT / "requirements.txt"
REGISTRY = ROOT / "config" / "model_registry.json"
PHASE4_PROVIDER = ROOT / "ssn" / "cognition" / "neuromorphic" / "learned_provider.py"
EVENT_BUS = ROOT / "ssn" / "cognition" / "event_bus.py"

APPROVED_ARTIFACT_SHA256 = (
    "dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc"
)


def _step(stream_id: str, index: int, channels=None, event_id: str | None = None) -> NeuromorphicEvent:
    if channels is None:
        channels = [0, 1, 0, 1, 0, 1, 0, 1]
    return NeuromorphicEvent(
        event_id=event_id or f"{stream_id}-t{index}",
        modality=STREAMING_MODALITY,
        features={
            "stream_id": stream_id,
            "sequence_index": index,
            "channels": list(channels),
        },
    )


def _reset(stream_id: str) -> NeuromorphicEvent:
    return NeuromorphicEvent(
        event_id=f"{stream_id}-reset",
        modality=STREAMING_MODALITY,
        features={"stream_id": stream_id, "lifecycle_op": "stream_reset"},
    )


class TestPhase5AStreamingReadiness(unittest.TestCase):
    def test_phase4_prerequisites_remain_accepted_and_immutable(self):
        phase4 = json.loads(PHASE4_ACCEPTANCE.read_text(encoding="utf-8"))
        self.assertEqual(phase4["decision"], "PHASE_4_ACCEPTED")
        self.assertEqual(phase4["adr_0004_status"], "ACCEPTED_PHASE_4")
        self.assertEqual(phase4["accepted_evidence_baseline"], "05de2b04279a72ece4834a984461a505de1188b3")
        self.assertEqual(
            phase4["provider"]["artifact_path"],
            "artifacts/neuromorphic/phase4b-lif-final-membrane-v1.json",
        )
        self.assertEqual(phase4["provider"]["artifact_sha256"], APPROVED_ARTIFACT_SHA256)
        digest = hashlib.sha256(ARTIFACT.read_bytes()).hexdigest()
        self.assertEqual(digest, APPROVED_ARTIFACT_SHA256)
        adr4 = ADR4.read_text(encoding="utf-8")
        block4 = adr4.replace("\r\n", "\n").split("## Status", 1)[1].split("## Context", 1)[0]
        self.assertIn("Accepted (Phase 4)", block4)

    def test_phase5_planning_accepted_and_adr0005_remains_proposed(self):
        planning = json.loads(PHASE5_PLAN.read_text(encoding="utf-8"))
        self.assertEqual(planning["decision"], "PHASE_5_PLANNING_ACCEPTED")
        self.assertEqual(planning["adr_0005_status"], "PROPOSED")
        adr5 = ADR5.read_text(encoding="utf-8")
        block5 = adr5.replace("\r\n", "\n").split("## Status", 1)[1].split("## Context", 1)[0]
        self.assertRegex(block5, r"(?m)^\s*Proposed\s*$")
        self.assertNotIn("Accepted", block5)
        status = STATUS.read_text(encoding="utf-8")
        self.assertIn("Phase 5 | **Planning accepted", status)
        self.assertIn("ADR 0005 **Proposed**", status)
        self.assertNotRegex(status, r"(?m)^\| Phase 5 \| \*\*Completed")

    def test_contract_freezes_identity_dimensions_bounds_and_ttl(self):
        contract = load_streaming_contract()
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(contract["provider"]["reserved_id"], RESERVED_PROVIDER_ID)
        self.assertFalse(contract["provider"]["global_default"])
        self.assertFalse(contract["provider"]["implementation_accepted"])
        dims = contract["temporal_dimensions"]
        self.assertEqual(dims["timesteps"], 20)
        self.assertEqual(dims["channels_per_step"], 8)
        self.assertEqual(dims["sequence_index_min"], 0)
        self.assertEqual(dims["sequence_index_max"], 19)
        bounds = contract["bounds"]
        self.assertEqual(bounds["max_active_learned_streams"], 256)
        self.assertEqual(bounds["max_stream_id_chars"], 128)
        self.assertEqual(bounds["max_stored_temporal_raw_payload_history"], 0)
        ttl = contract["idle_ttl"]
        self.assertEqual(ttl["value"], 30000)
        self.assertEqual(ttl["unit"], "milliseconds")
        self.assertGreater(ttl["value"], 0)
        self.assertEqual(contract["capacity_policy"]["on_limit_reached"], "FAIL_CLOSED")
        self.assertTrue(contract["capacity_policy"]["silent_eviction_of_active_streams_forbidden"])
        self.assertTrue(contract["capacity_policy"]["lru_eviction_of_active_streams_forbidden"])
        self.assertEqual(evidence["decision"], "PHASE5_STREAMING_READINESS_VERIFIED")
        self.assertEqual(evidence["provider_id_reserved"], RESERVED_PROVIDER_ID)
        self.assertEqual(evidence["idle_ttl"]["value"], 30000)
        self.assertEqual(evidence["idle_ttl"]["unit"], "milliseconds")
        self.assertEqual(evidence["next_blocker"], "EXP-5-002_STATEFUL_PROVIDER_IMPLEMENTATION_AND_FULL_PHASE_4_PARITY")
        self.assertIn("siona-neuro-streaming-lif-v1", READINESS_DOC.read_text(encoding="utf-8"))

    def test_binary_numeric_and_sequence_range_are_strict(self):
        validate_streaming_step_event(_step("alpha", 0))
        validate_streaming_step_event(_step("alpha", 19))
        with self.assertRaises(StreamingLifecycleError):
            validate_streaming_step_event(_step("alpha", -1))
        with self.assertRaises(StreamingLifecycleError):
            validate_streaming_step_event(_step("alpha", 20))
        with self.assertRaises(StreamingLifecycleError):
            validate_streaming_step_event(_step("alpha", True))  # type: ignore[arg-type]
        with self.assertRaises(StreamingLifecycleError):
            validate_streaming_step_event(_step("alpha", 0, channels=["1"] * 8))
        with self.assertRaises(StreamingLifecycleError):
            validate_streaming_step_event(_step("alpha", 0, channels=[1, 0, 1, 0, 1, 0, 1]))
        with self.assertRaises(StreamingLifecycleError):
            validate_streaming_step_event(_step("alpha", 0, channels=[0.5] + [0] * 7))
        with self.assertRaises(StreamingLifecycleError):
            validate_streaming_step_event(_step("alpha", 0, channels=[math.nan] + [0] * 7))
        with self.assertRaises(StreamingLifecycleError):
            validate_streaming_step_event(_step("alpha", 0, channels=[math.inf] + [0] * 7))
        with self.assertRaises(StreamingLifecycleError):
            validate_streaming_step_event(_step("alpha", 0, channels=[True] + [0] * 7))
        with self.assertRaises(StreamingLifecycleError):
            validate_streaming_step_event(_step("x" * 129, 0))

    def test_duplicate_skipped_out_of_order_and_post_completion_are_rejected(self):
        tracker = StreamingLifecycleTracker()
        tracker.ingest_step(_step("s", 0))
        with self.assertRaises(StreamingLifecycleError) as duplicate:
            tracker.ingest_step(_step("s", 0))
        self.assertIn("DUPLICATE", str(duplicate.exception))
        with self.assertRaises(StreamingLifecycleError) as skipped:
            tracker.ingest_step(_step("s", 2))
        self.assertIn("SKIPPED", str(skipped.exception))
        tracker.ingest_step(_step("s", 1))
        with self.assertRaises(StreamingLifecycleError) as backwards:
            tracker.ingest_step(_step("s", 0))
        self.assertIn("BACKWARDS", str(backwards.exception))
        for index in range(2, 20):
            tracker.ingest_step(_step("s", index))
        self.assertEqual(tracker.state_of("s"), "COMPLETED")
        with self.assertRaises(StreamingLifecycleError) as completed:
            tracker.ingest_step(_step("s", 0))
        self.assertIn("COMPLETED", str(completed.exception))
        self.assertEqual(tracker.state_of("s"), "COMPLETED")

    def test_malformed_input_cannot_mutate_successful_state(self):
        tracker = StreamingLifecycleTracker()
        tracker.ingest_step(_step("s", 0))
        before = tracker.snapshot()
        success_before = tracker.success_count
        failures_before = tracker.failure_count
        with self.assertRaises(StreamingLifecycleError):
            tracker.ingest_step(_step("s", 0, channels=["1"] * 8))
        self.assertEqual(tracker.snapshot(), before)
        self.assertEqual(tracker.success_count, success_before)
        self.assertEqual(tracker.failure_count, failures_before + 1)
        self.assertEqual(before["s"].raw_payload_history, ())

    def test_stream_and_provider_reset_semantics(self):
        tracker = StreamingLifecycleTracker()
        tracker.ingest_step(_step("a", 0))
        tracker.ingest_step(_step("b", 0))
        tracker.reset_stream(_reset("a"))
        self.assertEqual(tracker.state_of("a"), "NONEXISTENT")
        self.assertEqual(tracker.state_of("b"), "ACTIVE")
        tracker.ingest_step(_step("a", 0))
        tracker.reset_provider()
        self.assertEqual(tracker.state_of("a"), "NONEXISTENT")
        self.assertEqual(tracker.state_of("b"), "NONEXISTENT")
        self.assertEqual(tracker.resident_count, 0)

    def test_idle_expiry_removes_only_expired_stream_and_requires_new_lifecycle(self):
        clock = {"now": 0.0}

        def now() -> float:
            return clock["now"]

        tracker = StreamingLifecycleTracker(now=now)
        tracker.ingest_step(_step("keep", 0))
        tracker.ingest_step(_step("stale", 0))
        clock["now"] = 25.0
        tracker.ingest_step(_step("keep", 1))
        clock["now"] = 50.001
        tracker.ingest_step(_step("keep", 2))
        self.assertEqual(tracker.state_of("keep"), "ACTIVE")
        self.assertEqual(tracker.state_of("stale"), "NONEXISTENT")
        with self.assertRaises(StreamingLifecycleError):
            tracker.ingest_step(_step("stale", 1))
        tracker.ingest_step(_step("stale", 0))
        self.assertEqual(tracker.state_of("stale"), "ACTIVE")

    def test_capacity_fail_closed_without_silent_active_eviction(self):
        clock = {"now": 0.0}
        tracker = StreamingLifecycleTracker(now=lambda: clock["now"])
        for index in range(256):
            tracker.ingest_step(_step(f"stream-{index:03d}", 0))
        self.assertEqual(tracker.resident_count, 256)
        with self.assertRaises(StreamingLifecycleError) as exhausted:
            tracker.ingest_step(_step("overflow", 0))
        self.assertIn("CAPACITY", str(exhausted.exception))
        self.assertEqual(tracker.resident_count, 256)
        self.assertEqual(tracker.state_of("stream-000"), "ACTIVE")
        self.assertEqual(tracker.state_of("overflow"), "NONEXISTENT")
        clock["now"] = 30.001
        tracker.ingest_step(_step("overflow", 0))
        self.assertEqual(tracker.state_of("overflow"), "ACTIVE")
        self.assertLessEqual(tracker.resident_count, 256)

    def test_multi_stream_isolation_requirement_is_frozen_and_lifecycle_isolated(self):
        contract = load_streaming_contract()
        self.assertTrue(contract["multi_stream_isolation"]["required"])
        interleaved = StreamingLifecycleTracker()
        independent = StreamingLifecycleTracker()
        for index in range(20):
            interleaved.ingest_step(_step("A", index))
            interleaved.ingest_step(_step("B", index))
        for index in range(20):
            independent.ingest_step(_step("A", index))
        for index in range(20):
            independent.ingest_step(_step("B", index))
        self.assertEqual(interleaved.state_of("A"), independent.state_of("A"))
        self.assertEqual(interleaved.state_of("B"), independent.state_of("B"))
        self.assertEqual(interleaved.snapshot()["A"].next_expected_sequence_index, 20)
        self.assertEqual(interleaved.snapshot()["B"].next_expected_sequence_index, 20)
        self.assertEqual(interleaved.snapshot()["A"].raw_payload_history, ())

    def test_future_parity_thresholds_and_non_claims(self):
        evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        parity = evidence["future_phase4_parity"]
        self.assertEqual(parity["frozen_test_samples"], 128)
        self.assertEqual(parity["predicted_class_agreement_required"], 128)
        self.assertEqual(parity["spike_count_agreement_required"], 128)
        self.assertEqual(parity["max_abs_logit_difference"], 1e-12)
        self.assertEqual(parity["max_abs_probability_difference"], 1e-12)
        self.assertFalse(parity["executed"])
        self.assertEqual(evidence["training_run_count"], 0)
        self.assertEqual(evidence["qwen_run_count"], 0)
        self.assertEqual(evidence["network_calls"], 0)
        self.assertEqual(evidence["subprocess_calls"], 0)
        self.assertEqual(evidence["tool_execution_count"], 0)
        self.assertFalse(evidence["tool_authority"])
        self.assertFalse(evidence["physical_actuation_authority"])
        self.assertFalse(evidence["requirements_changed"])
        self.assertFalse(evidence["model_registry_changed"])
        self.assertFalse(evidence["artifact_mutated"])
        self.assertFalse(evidence["async_event_bus_integrated"])
        self.assertEqual(evidence["adr_0005_status"], "PROPOSED")
        self.assertEqual(evidence["phase_5_status"], "IN_PROGRESS")
        self.assertFalse(evidence["phase_5_implementation_accepted"])

        requirements = REQUIREMENTS.read_text(encoding="utf-8").lower()
        for package in ("torch", "snntorch", "norse"):
            self.assertNotIn(package, requirements)
        source = PHASE4_PROVIDER.read_text(encoding="utf-8")
        self.assertNotIn("import torch", source)
        self.assertNotIn("import snntorch", source)
        helper = (ROOT / "ssn" / "cognition" / "neuromorphic" / "phase5a_streaming_contract.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("import torch", helper)
        self.assertNotIn("import snntorch", helper)

        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        qwen = next(m for m in registry["models"] if m["provider_id"] == "siona-local-open-weight-v1")
        self.assertTrue(qwen["capabilities"]["chat"])
        self.assertFalse(qwen["capabilities"]["tools"])
        self.assertFalse(qwen["capabilities"]["streaming"])
        bus = EVENT_BUS.read_text(encoding="utf-8")
        self.assertIn("class AsyncEventBus", bus)
        self.assertNotIn("siona-neuro-streaming-lif-v1", bus)
        self.assertIn("EXP-5-002", ROADMAP.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
