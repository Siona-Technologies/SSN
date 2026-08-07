"""EXP-4-004 learned SNN provider/parity regressions (model-free)."""

from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path

from ssn.cognition.neuromorphic.contracts import NeuromorphicEvent
from ssn.cognition.neuromorphic.learned_artifact import (
    APPROVED_ARTIFACT_SHA256,
    load_learned_artifact,
)
from ssn.cognition.neuromorphic.learned_inference import (
    forward_lif_final_membrane,
    parse_temporal_sequence,
)
from ssn.cognition.neuromorphic.learned_provider import (
    LEARNED_FEATURE_KEY,
    LEARNED_MODALITY,
    LearnedNeuromorphicInputError,
    LearnedTemporalSalienceProvider,
)
from ssn.cognition.neuromorphic.legacy_adapter import NeuromorphicSNNFacade
from ssn.cognition.neuromorphic.phase4a_dataset import generate_split
from ssn.cognition.neuromorphic.providers import DeterministicNeuromorphicProvider

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts" / "neuromorphic" / "phase4b-lif-final-membrane-v1.json"
PARITY_FIXTURE = ROOT / "docs" / "evidence" / "EXP-4-004_PARITY_FIXTURE.json"
PARITY_EVIDENCE = ROOT / "docs" / "evidence" / "EXP-4-004_LEARNED_SNN_PROVIDER_PARITY.json"
REQUIREMENTS = ROOT / "requirements.txt"
REGISTRY = ROOT / "config" / "model_registry.json"
ADR4 = ROOT / "docs" / "adr" / "0004-learned-neuromorphic-backend-strategy.md"


class TestLearnedSnnProvider(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = LearnedTemporalSalienceProvider()

    def test_canonical_artifact_and_authority(self) -> None:
        raw = ARTIFACT.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), APPROVED_ARTIFACT_SHA256)
        art = load_learned_artifact()
        self.assertEqual(art["provider_target"], "siona-neuro-learned-lif-v1")
        self.assertFalse(art["tool_authority"])
        self.assertFalse(art["physical_actuation_authority"])

    def test_valid_temporal_input_is_deterministic_and_advisory(self) -> None:
        sample = generate_split("test")[0]
        event = NeuromorphicEvent(
            event_id="t0",
            modality=LEARNED_MODALITY,
            features={LEARNED_FEATURE_KEY: [list(row) for row in sample.sequence]},
        )
        out1 = self.provider.process_event(event)
        out2 = self.provider.process_event(event)
        self.assertEqual(out1.signal_strength, out2.signal_strength)
        self.assertEqual(out1.spikes_detected, out2.spikes_detected)
        self.assertEqual(out1.meta["predicted_class"], out2.meta["predicted_class"])
        self.assertIsNone(out1.reflex_proposal)
        self.assertFalse(out1.meta["tool_authority"])
        self.assertFalse(out1.meta["physical_actuation_authority"])
        self.assertTrue(out1.meta["trained"])
        self.assertTrue(out1.meta["software_snn"])
        self.assertFalse(out1.meta["hardware_neuromorphic"])

    def test_malformed_learned_input_fails_closed(self) -> None:
        bad = NeuromorphicEvent(
            event_id="bad",
            modality=LEARNED_MODALITY,
            features={LEARNED_FEATURE_KEY: [[0] * 8 for _ in range(19)]},
        )
        before = self.provider.get_state().step
        with self.assertRaises(LearnedNeuromorphicInputError):
            self.provider.process_event(bad)
        self.assertEqual(self.provider.get_state().step, before)

    def test_unsupported_modality_falls_back_explicitly(self) -> None:
        event = NeuromorphicEvent(event_id="u", modality="text", features={"text": "hello"})
        out = self.provider.process_event(event)
        self.assertTrue(out.meta.get("learned_provider_fallback"))
        self.assertEqual(out.meta.get("fallback_reason"), "unsupported_modality")
        self.assertIsNone(out.reflex_proposal)
        self.assertEqual(out.backend, "siona-neuro-deterministic-v1")

    def test_default_facade_unchanged_and_explicit_injection(self) -> None:
        default = NeuromorphicSNNFacade()
        self.assertIsInstance(default._provider, DeterministicNeuromorphicProvider)
        self.assertEqual(default.engine_name, "siona-neuro-deterministic-v1")

        learned = NeuromorphicSNNFacade(provider=self.provider)
        self.assertEqual(learned._provider.name, "siona-neuro-learned-lif-v1")

    def test_process_batch(self) -> None:
        samples = generate_split("test")[:3]
        events = [
            NeuromorphicEvent(
                event_id=s.sample_id,
                modality=LEARNED_MODALITY,
                features={LEARNED_FEATURE_KEY: [list(row) for row in s.sequence]},
            )
            for s in samples
        ]
        outs = self.provider.process_batch(events)
        self.assertEqual(len(outs), 3)
        self.assertTrue(all(o.backend == "siona-neuro-learned-lif-v1" for o in outs))

    def test_parity_fixture_matches_pure_python_without_torch(self) -> None:
        fixture = json.loads(PARITY_FIXTURE.read_text(encoding="utf-8"))
        self.assertEqual(fixture["artifact_sha256"], APPROVED_ARTIFACT_SHA256)
        self.assertEqual(len(fixture["samples"]), 5)
        art = load_learned_artifact()
        weights = art["weights"]
        for sample in fixture["samples"]:
            pure = forward_lif_final_membrane(
                parse_temporal_sequence(sample["sequence"]),
                fc1_weight=weights["fc1.weight"],
                fc1_bias=weights["fc1.bias"],
                fc2_weight=weights["fc2.weight"],
                fc2_bias=weights["fc2.bias"],
            )
            self.assertLessEqual(
                max(abs(a - b) for a, b in zip(pure["logits"], sample["reference_logits"])),
                fixture["tolerances"]["max_abs_logit_difference"],
            )
            self.assertLessEqual(
                max(abs(a - b) for a, b in zip(pure["probabilities"], sample["reference_probabilities"])),
                fixture["tolerances"]["max_abs_probability_difference"],
            )
            self.assertEqual(pure["predicted_class"], sample["predicted_class"])
            self.assertEqual(pure["hidden_spike_count"], sample["hidden_spike_count"])

    def test_historical_exp4004_and_current_adr_status_are_distinct(self) -> None:
        evidence = json.loads(PARITY_EVIDENCE.read_text(encoding="utf-8"))
        self.assertEqual(evidence["experiment_id"], "EXP-4-004")
        self.assertEqual(evidence["decision"], "LEARNED_SNN_PROVIDER_PARITY_VERIFIED")
        self.assertEqual(evidence["training_run_count"], 0)
        self.assertEqual(evidence["adr_0004_status"], "PROPOSED")

        adr = ADR4.read_text(encoding="utf-8")
        block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split("## Context", 1)[0]
        self.assertIn("Accepted (Phase 4)", block)

    def test_requirements_and_qwen_registry_boundaries(self) -> None:
        req = [
            line.strip().lower()
            for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        names = {line.split("==", 1)[0].split(">=", 1)[0].split("<=", 1)[0] for line in req}
        self.assertNotIn("torch", names)
        self.assertNotIn("snntorch", names)
        self.assertNotIn("norse", names)

        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
        entry = next(
            m
            for m in registry["models"]
            if m["provider_id"] == "siona-local-open-weight-v1"
            and m["model_id"] == "Qwen3-1.7B-Q4_K_M"
        )
        self.assertTrue(entry["capabilities"]["chat"])
        self.assertFalse(entry["capabilities"]["tools"])
        self.assertFalse(entry["capabilities"]["structured_json"])
        self.assertFalse(entry["capabilities"]["streaming"])
        self.assertFalse(entry["capabilities"]["multimodal"])


if __name__ == "__main__":
    unittest.main()
