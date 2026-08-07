"""EXP-4-005 Phase 4 learned SNN breadth / safety / evidence gate (model-free)."""

from __future__ import annotations

import copy
import hashlib
import inspect
import json
import math
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List

from ssn.cognition.neuromorphic.contracts import NeuromorphicEvent
from ssn.cognition.neuromorphic.learned_artifact import (
    APPROVED_ARTIFACT_SHA256,
    MAX_ARTIFACT_BYTES,
    LearnedNeuromorphicArtifactError,
    load_learned_artifact,
)
from ssn.cognition.neuromorphic.learned_provider import (
    LEARNED_FEATURE_KEY,
    LEARNED_MODALITY,
    MAX_EVENT_ID_CHARS,
    MAX_LEARNED_BATCH_EVENTS,
    LearnedNeuromorphicInputError,
    LearnedTemporalSalienceProvider,
)
from ssn.cognition.neuromorphic.phase4a_dataset import generate_split

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts" / "neuromorphic" / "phase4b-lif-final-membrane-v1.json"
REQUIREMENTS = ROOT / "requirements.txt"
REGISTRY = ROOT / "config" / "model_registry.json"
PROVIDER_MOD = ROOT / "ssn" / "cognition" / "neuromorphic" / "learned_provider.py"
ARTIFACT_MOD = ROOT / "ssn" / "cognition" / "neuromorphic" / "learned_artifact.py"
INFERENCE_MOD = ROOT / "ssn" / "cognition" / "neuromorphic" / "learned_inference.py"


def _write_artifact(payload: dict, path: Path) -> str:
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    path.write_bytes(blob)
    return hashlib.sha256(blob).hexdigest()


def _learned_event(sample_id: str, sequence: List[List[int]]) -> NeuromorphicEvent:
    return NeuromorphicEvent(
        event_id=sample_id,
        modality=LEARNED_MODALITY,
        features={LEARNED_FEATURE_KEY: sequence},
    )


class TestPhase4DLearnedSnnBreadthSafety(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = LearnedTemporalSalienceProvider()
        self.canonical = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.test_samples = generate_split("test")

    def test_no_in_memory_artifact_injection_parameter(self) -> None:
        params = inspect.signature(LearnedTemporalSalienceProvider.__init__).parameters
        self.assertNotIn("artifact", params)
        with self.assertRaises(TypeError):
            LearnedTemporalSalienceProvider(artifact={"sha256": APPROVED_ARTIFACT_SHA256})  # type: ignore[call-arg]

    def test_bounded_artifact_read_rejects_oversized_without_full_slurp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "huge.json"
            # Write larger than MAX without attempting to load as JSON in memory via read_bytes of whole repo.
            with path.open("wb") as handle:
                handle.write(b"{" + b"a" * (MAX_ARTIFACT_BYTES + 64) + b"}")
            with self.assertRaises(LearnedNeuromorphicArtifactError) as ctx:
                load_learned_artifact(path, expected_sha256="00" * 32)
            self.assertIn("artifact_too_large", str(ctx.exception))

    def test_strict_learned_event_envelope(self) -> None:
        good_seq = [list(row) for row in self.test_samples[0].sequence]
        # empty event_id
        with self.assertRaises(LearnedNeuromorphicInputError):
            self.provider.process_event(
                NeuromorphicEvent(event_id="", modality=LEARNED_MODALITY, features={LEARNED_FEATURE_KEY: good_seq})
            )
        # too long event_id
        with self.assertRaises(LearnedNeuromorphicInputError):
            self.provider.process_event(
                NeuromorphicEvent(
                    event_id="x" * (MAX_EVENT_ID_CHARS + 1),
                    modality=LEARNED_MODALITY,
                    features={LEARNED_FEATURE_KEY: good_seq},
                )
            )
        # extra feature keys
        with self.assertRaises(LearnedNeuromorphicInputError):
            self.provider.process_event(
                NeuromorphicEvent(
                    event_id="e1",
                    modality=LEARNED_MODALITY,
                    features={LEARNED_FEATURE_KEY: good_seq, "extra": 1},
                )
            )
        # non-event object
        with self.assertRaises(LearnedNeuromorphicInputError):
            self.provider.process_event({"modality": LEARNED_MODALITY})  # type: ignore[arg-type]

    def test_malformed_inputs_fail_closed_without_state_mutation(self) -> None:
        before = self.provider.get_state().step
        before_health = self.provider.health()
        bad_cases = [
            [[0] * 8 for _ in range(19)],
            [[0] * 7 for _ in range(20)],
            [[0] * 8 for _ in range(19)] + [[True] + [0] * 7],
            [[0] * 8 for _ in range(19)] + [[2] + [0] * 7],
            [[0] * 8 for _ in range(19)] + [[-1] + [0] * 7],
            [[0] * 8 for _ in range(19)] + [[float("nan")] + [0] * 7],
            [[0] * 8 for _ in range(19)] + [[float("inf")] + [0] * 7],
            [[0] * 8 for _ in range(19)] + [["x"] * 8],
        ]
        for seq in bad_cases:
            with self.assertRaises(LearnedNeuromorphicInputError):
                self.provider.process_event(_learned_event("bad", seq))
        after = self.provider.get_state().step
        after_health = self.provider.health()
        self.assertEqual(before, after)
        self.assertEqual(before_health["learned_events"], after_health["learned_events"])
        self.assertEqual(before_health["events"], after_health["events"])
        self.assertGreater(after_health["rejected_inputs"], before_health["rejected_inputs"])

    def test_batch_limit_and_atomicity(self) -> None:
        good = _learned_event("g0", [list(r) for r in self.test_samples[0].sequence])
        # oversized batch
        huge = [good] * (MAX_LEARNED_BATCH_EVENTS + 1)
        before = self.provider.health()
        with self.assertRaises(LearnedNeuromorphicInputError):
            self.provider.process_batch(huge)
        mid = self.provider.health()
        self.assertEqual(before["learned_events"], mid["learned_events"])
        self.assertEqual(before["events"], mid["events"])

        # generator rejected
        with self.assertRaises(LearnedNeuromorphicInputError):
            self.provider.process_batch(e for e in [good])  # type: ignore[arg-type]

        # mixed malformed batch: no partial mutation
        bad = _learned_event("bad", [[0] * 8 for _ in range(19)])
        batch = [
            _learned_event("g1", [list(r) for r in self.test_samples[1].sequence]),
            _learned_event("g2", [list(r) for r in self.test_samples[2].sequence]),
            bad,
            _learned_event("g3", [list(r) for r in self.test_samples[3].sequence]),
        ]
        before2 = self.provider.health()
        step_before = self.provider.get_state().step
        with self.assertRaises(LearnedNeuromorphicInputError):
            self.provider.process_batch(batch)
        after2 = self.provider.health()
        self.assertEqual(before2["learned_events"], after2["learned_events"])
        self.assertEqual(before2["events"], after2["events"])
        self.assertEqual(step_before, self.provider.get_state().step)

    def test_full_frozen_test_breadth(self) -> None:
        preds: List[int] = []
        labels: List[int] = []
        for sample in self.test_samples:
            out = self.provider.process_event(
                _learned_event(sample.sample_id, [list(r) for r in sample.sequence])
            )
            self.assertIsNone(out.reflex_proposal)
            self.assertFalse(out.meta["tool_authority"])
            self.assertFalse(out.meta["physical_actuation_authority"])
            preds.append(int(out.meta["predicted_class"]))
            labels.append(int(sample.label))
        self.assertEqual(len(preds), 128)
        correct = sum(int(p == y) for p, y in zip(preds, labels))
        self.assertEqual(correct, 128)
        recalls = {}
        for cls in (0, 1):
            idx = [i for i, y in enumerate(labels) if y == cls]
            recalls[cls] = sum(preds[i] == cls for i in idx) / len(idx)
        bal = (recalls[0] + recalls[1]) / 2.0
        self.assertEqual(recalls[0], 1.0)
        self.assertEqual(recalls[1], 1.0)
        self.assertEqual(bal, 1.0)

    def test_temporal_reversal_breadth(self) -> None:
        positives = [s for s in self.test_samples if s.label == 1]
        self.assertEqual(len(positives), 64)
        original_scores = []
        reversed_scores = []
        for sample in positives:
            seq = [list(r) for r in sample.sequence]
            rev = list(reversed(seq))
            o = self.provider.process_event(_learned_event(f"o-{sample.sample_id}", seq))
            r = self.provider.process_event(_learned_event(f"r-{sample.sample_id}", rev))
            original_scores.append(float(o.signal_strength))
            reversed_scores.append(float(r.signal_strength))
        mean_o = sum(original_scores) / len(original_scores)
        mean_r = sum(reversed_scores) / len(reversed_scores)
        drop = mean_o - mean_r
        self.assertGreaterEqual(drop, 0.90)
        # stash for evidence helpers
        self._temporal = {"mean_o": mean_o, "mean_r": mean_r, "drop": drop}

    def test_edge_controls(self) -> None:
        zero = [[0 for _ in range(8)] for _ in range(20)]
        ones = [[1 for _ in range(8)] for _ in range(20)]
        early = [row[:] for row in zero]
        early[0][0] = 1
        late = [row[:] for row in zero]
        late[19][7] = 1
        first_all = [row[:] for row in zero]
        first_all[0] = [1] * 8
        last_all = [row[:] for row in zero]
        last_all[19] = [1] * 8
        alt_t = [[1 if t % 2 == 0 else 0 for _ in range(8)] for t in range(20)]
        alt_c = [[1 if c % 2 == 0 else 0 for c in range(8)] for _ in range(20)]
        controls = [zero, ones, early, late, first_all, last_all, alt_t, alt_c, zero]
        for i, seq in enumerate(controls):
            out1 = self.provider.process_event(_learned_event(f"edge-{i}-a", seq))
            out2 = self.provider.process_event(_learned_event(f"edge-{i}-b", seq))
            self.assertEqual(out1.signal_strength, out2.signal_strength)
            self.assertEqual(out1.meta["predicted_class"], out2.meta["predicted_class"])
            self.assertEqual(out1.spikes_detected, out2.spikes_detected)
            probs = out1.salience.components
            self.assertTrue(0.0 <= probs["class_0_probability"] <= 1.0)
            self.assertTrue(0.0 <= probs["class_1_probability"] <= 1.0)
            self.assertAlmostEqual(
                probs["class_0_probability"] + probs["class_1_probability"],
                1.0,
                places=12,
            )
            self.assertIn(out1.meta["predicted_class"], (0, 1))
            self.assertGreaterEqual(out1.spikes_detected, 0)
            self.assertTrue(math.isfinite(out1.signal_strength))
            self.assertIsNone(out1.reflex_proposal)
            self.assertFalse(out1.meta["tool_authority"])
            self.assertFalse(out1.meta["physical_actuation_authority"])

    def test_fallback_modalities(self) -> None:
        modalities = ["text", "audio", "vision", "lidar", "radar", "imu", "unknown"]
        for modality in modalities:
            out = self.provider.process_event(
                NeuromorphicEvent(event_id=f"fb-{modality}", modality=modality, features={"text": "x"})
            )
            self.assertTrue(out.meta.get("learned_provider_fallback"))
            self.assertEqual(out.meta.get("fallback_reason"), "unsupported_modality")
            self.assertLessEqual(len(out.meta.get("fallback_reason", "")), 64)
            self.assertIsNone(out.reflex_proposal)
            self.assertFalse(out.meta.get("tool_authority", False))
            self.assertFalse(out.meta.get("physical_actuation_authority", False))
            self.assertNotEqual(out.backend, "siona-neuro-learned-lif-v1")

    def test_corrupted_artifact_matrix(self) -> None:
        cases: List[Dict[str, Any]] = []
        base = copy.deepcopy(self.canonical)

        def add(mutator) -> None:
            p = copy.deepcopy(base)
            mutator(p)
            cases.append(p)

        add(lambda p: p.__setitem__("provider_target", "wrong"))
        add(lambda p: p.__setitem__("task_id", "wrong"))
        add(lambda p: p.__setitem__("architecture_id", "wrong"))
        add(lambda p: p.__setitem__("training_experiment", "EXP-X"))
        add(lambda p: p.__setitem__("training_seed", 1))
        add(lambda p: p.__setitem__("tool_authority", True))
        add(lambda p: p.__setitem__("physical_actuation_authority", True))
        add(lambda p: p["dataset_fingerprints"].__setitem__("test", "0" * 64))
        add(lambda p: p["weights"]["fc1.bias"].__setitem__(0, float("nan")))
        add(lambda p: p["weights"]["fc2.bias"].__setitem__(0, float("inf")))
        add(lambda p: p["weights"]["fc1.bias"].__setitem__(0, True))
        add(lambda p: p["weights"].__setitem__("fc1.weight", [[0.0] * 7 for _ in range(16)]))
        add(lambda p: p["weights"].__setitem__("fc2.weight", [[0.0] * 16]))
        add(lambda p: p["weights"]["fc2.bias"].__setitem__(0, 0.123456789))
        add(lambda p: p.pop("lif"))
        add(lambda p: p.__setitem__("extra_root", True))

        for payload in cases:
            with tempfile.TemporaryDirectory() as tmp:
                path = Path(tmp) / "bad.json"
                digest = _write_artifact(payload, path)
                with self.assertRaises(LearnedNeuromorphicArtifactError):
                    load_learned_artifact(path, expected_sha256=digest)
                with self.assertRaises(LearnedNeuromorphicArtifactError):
                    LearnedTemporalSalienceProvider(artifact_path=path, expected_sha256=digest)

        # wrong SHA against approved constant
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mut.json"
            payload = copy.deepcopy(base)
            payload["weights"]["fc2.bias"][0] = 0.42
            digest = _write_artifact(payload, path)
            self.assertNotEqual(digest, APPROVED_ARTIFACT_SHA256)
            with self.assertRaises(LearnedNeuromorphicArtifactError):
                load_learned_artifact(path, expected_sha256=APPROVED_ARTIFACT_SHA256)

        # duplicate key
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "dup.json"
            path.write_text('{"schema_version":1,"schema_version":2}', encoding="utf-8")
            with self.assertRaises(LearnedNeuromorphicArtifactError):
                load_learned_artifact(path, expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest())

        # invalid UTF-8
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bin.json"
            path.write_bytes(b"\xff\xfe{" )
            with self.assertRaises(LearnedNeuromorphicArtifactError):
                load_learned_artifact(path, expected_sha256=hashlib.sha256(path.read_bytes()).hexdigest())

        # malformed JSON
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "badjson.json"
            raw = b"{not-json"
            path.write_bytes(raw)
            with self.assertRaises(LearnedNeuromorphicArtifactError):
                load_learned_artifact(path, expected_sha256=hashlib.sha256(raw).hexdigest())

    def test_dependency_isolation_stdlib_only(self) -> None:
        banned = ("torch", "snntorch", "numpy", "norse")
        for path in (PROVIDER_MOD, ARTIFACT_MOD, INFERENCE_MOD):
            text = path.read_text(encoding="utf-8")
            for name in banned:
                self.assertNotRegex(text, rf"(?m)^\s*import\s+{name}\b")
                self.assertNotRegex(text, rf"(?m)^\s*from\s+{name}\b")
            self.assertNotIn("subprocess", text)
            self.assertNotIn("urllib", text)
            self.assertNotIn("socket", text)

        req = [
            line.strip().lower()
            for line in REQUIREMENTS.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        names = {line.split("==", 1)[0].split(">=", 1)[0].split("<=", 1)[0] for line in req}
        for name in banned:
            self.assertNotIn(name, names)

    def test_authority_and_capability_honesty(self) -> None:
        caps = self.provider.capabilities()
        self.assertFalse(caps.energy_metrics)
        self.assertTrue(caps.metadata["trained"])
        self.assertTrue(caps.metadata["learned"])
        self.assertTrue(caps.metadata["software_snn"])
        self.assertFalse(caps.metadata["hardware_neuromorphic"])
        self.assertFalse(caps.metadata["tool_authority"])
        self.assertFalse(caps.metadata["physical_actuation_authority"])
        health = self.provider.health()
        self.assertFalse(health["energy_metrics"])
        self.assertIn("compatibility", health["energy_note"])

        sample = self.test_samples[0]
        out = self.provider.process_event(
            _learned_event(sample.sample_id, [list(r) for r in sample.sequence])
        )
        self.assertEqual(out.energy, 0.0)
        self.assertIsNone(out.reflex_proposal)

    def test_reset_restores_baseline(self) -> None:
        sample = self.test_samples[0]
        self.provider.process_event(_learned_event("r1", [list(r) for r in sample.sequence]))
        self.provider.process_event(NeuromorphicEvent(event_id="t", modality="text", features={"text": "x"}))
        try:
            self.provider.process_event(_learned_event("bad", [[0] * 8 for _ in range(19)]))
        except LearnedNeuromorphicInputError:
            pass
        self.provider.reset()
        health = self.provider.health()
        self.assertEqual(health["events"], 0)
        self.assertEqual(health["learned_events"], 0)
        self.assertEqual(health["fallback_events"], 0)
        self.assertEqual(health["rejected_inputs"], 0)
        self.assertEqual(self.provider.get_state().step, 0)

    def test_qwen_registry_unchanged(self) -> None:
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


if __name__ == "__main__":
    unittest.main()
