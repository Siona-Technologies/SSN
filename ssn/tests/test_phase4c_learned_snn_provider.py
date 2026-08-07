"""EXP-4-004 model-free learned SNN provider tests (no torch/snnTorch)."""

from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from ssn.cognition.neuromorphic.contracts import NeuromorphicEvent
from ssn.cognition.neuromorphic.learned_artifact import (
    APPROVED_ARTIFACT_SHA256,
    LearnedNeuromorphicArtifactError,
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
REQUIREMENTS = ROOT / "requirements.txt"
REGISTRY = ROOT / "config" / "model_registry.json"
ADR4 = ROOT / "docs" / "adr" / "0004-learned-neuromorphic-backend-strategy.md"


def _write_artifact(payload: dict, path: Path) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    path.write_bytes(blob)
    return hashlib.sha256(blob).hexdigest()


class TestLearnedSnnProvider(unittest.TestCase):
    def setUp(self) -> None:
        self.canonical = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.provider = LearnedTemporalSalienceProvider()

    def test_canonical_artifact_loads_with_exact_sha(self) -> None:
        art = load_learned_artifact()
        self.assertEqual(art["sha256"], APPROVED_ARTIFACT_SHA256)
        self.assertEqual(art["provider_target"], "siona-neuro-learned-lif-v1")
        self.assertFalse(art["tool_authority"])
        self.assertFalse(art["physical_actuation_authority"])

    def test_artifact_rejects_duplicate_extra_and_wrong_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text('{"schema_version":1,"schema_version":2}', encoding="utf-8")
            with self.assertRaises(LearnedNeuromorphicArtifactError):
                load_learned_artifact(path, expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest())

        for mutation in ("extra", "schema"):
            payload = copy.deepcopy(self.canonical)
            if mutation == "extra":
                payload["extra_root"] = True
            else:
                payload["schema_version"] = 2
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / f"{mutation}.json"
                digest = _write_artifact(payload, path)
                with self.assertRaises(LearnedNeuromorphicArtifactError):
                    load_learned_artifact(path, expected_sha256=digest)

    def test_artifact_rejects_wrong_identity_authority_nan_bool_shapes(self) -> None:
        cases = []
        base = copy.deepcopy(self.canonical)
        for mutator in (
            lambda p: p.__setitem__("provider_target", "wrong"),
            lambda p: p.__setitem__("task_id", "wrong"),
            lambda p: p.__setitem__("architecture_id", "wrong"),
            lambda p: p.__setitem__("tool_authority", True),
            lambda p: p.__setitem__("physical_actuation_authority", True),
            lambda p: p["weights"]["fc1.bias"].__setitem__(0, float("nan")),
            lambda p: p["weights"]["fc2.bias"].__setitem__(0, float("inf")),
            lambda p: p["weights"]["fc1.bias"].__setitem__(0, True),
            lambda p: p["weights"].__setitem__("fc1.weight", [[0.0] * 7 for _ in range(16)]),
            lambda p: p["weights"].__setitem__("fc2.weight", [[0.0] * 16]),
        ):
            p = copy.deepcopy(base)
            mutator(p)
            cases.append(p)

        for payload in cases:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "case.json"
                digest = _write_artifact(payload, path)
                with self.assertRaises(LearnedNeuromorphicArtifactError):
                    load_learned_artifact(path, expected_sha256=digest)

    def test_valid_temporal_input_and_determinism(self) -> None:
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

    def test_malformed_temporal_inputs_fail_closed(self) -> None:
        bad_cases = [
            [[0] * 8 for _ in range(19)],
            [[0] * 7 for _ in range(20)],
            [[0] * 8 for _ in range(19)] + [[True] + [0] * 7],
            [[0] * 8 for _ in range(19)] + [[2] + [0] * 7],
            [[0] * 8 for _ in range(19)] + [[float("nan")] + [0] * 7],
        ]
        for seq in bad_cases:
            event = NeuromorphicEvent(
                event_id="bad",
                modality=LEARNED_MODALITY,
                features={LEARNED_FEATURE_KEY: seq},
            )
            with self.assertRaises(LearnedNeuromorphicInputError):
                self.provider.process_event(event)

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
        learned_facade = NeuromorphicSNNFacade(provider=self.provider)
        self.assertEqual(learned_facade._provider.name, "siona-neuro-learned-lif-v1")

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
                max(abs(pure["logits"][i] - sample["reference_logits"][i]) for i in (0, 1)),
                fixture["tolerances"]["max_abs_logit_difference"],
            )
            self.assertLessEqual(
                max(abs(pure["probabilities"][i] - sample["reference_probabilities"][i]) for i in (0, 1)),
                fixture["tolerances"]["max_abs_probability_difference"],
            )
            self.assertEqual(pure["predicted_class"], sample["predicted_class"])
            self.assertEqual(pure["hidden_spike_count"], sample["hidden_spike_count"])

    def test_requirements_registry_and_current_adr_boundaries(self) -> None:
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

        adr = ADR4.read_text(encoding="utf-8")
        block = adr.replace("\r\n", "\n").split("## Status", 1)[1].split("## Context", 1)[0]
        self.assertIn("Accepted (Phase 4)", block)


if __name__ == "__main__":
    unittest.main()
