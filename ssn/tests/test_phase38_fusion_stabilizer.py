# ssn/tests/test_phase38_fusion_stabilizer.py

import unittest

from ssn.core.fusion_stabilizer import FusionStabilizer


class DummyMemoryHub:
    def __init__(self):
        self.traces = []

    def get_recent_traces(self, limit=120):
        return self.traces[:limit]


class AllowSafety:
    def allow_internal_reflection(self):
        return True


class DenySafety:
    def allow_internal_reflection(self):
        return False


class TestPhase38FusionStabilizer(unittest.TestCase):

    def test_compute_neutral_when_safety_denied(self):
        hub = DummyMemoryHub()
        stab = FusionStabilizer(memory_hub=hub, safety_monitor=DenySafety())
        adj = stab.compute()
        self.assertEqual(adj.drift_score, 0.0)
        self.assertEqual(adj.damping_factor, 0.0)
        self.assertEqual(adj.llm_weight_multiplier, 1.0)
        self.assertEqual(adj.snn_weight_multiplier, 1.0)

    def test_apply_damps_fusion_score_and_adds_stability_block(self):
        hub = DummyMemoryHub()
        # Provide drift + prefs so damping/style hints kick in
        hub.traces = [
            {"payload": {"type": "drift_report", "drift_score": 0.70, "drift_tags": ["mode_oscillation"]}},
            {"payload": {"type": "preference_update", "stable_candidates": [{"key": "writing_style", "value": "concise", "confidence": 0.8}]}},
        ]

        stab = FusionStabilizer(memory_hub=hub, safety_monitor=AllowSafety())
        fusion = {"fusion_score": 0.90, "mode": "deep"}

        out = stab.apply_to_fusion_result(fusion)

        self.assertIn("stability", out)
        self.assertIn("damping_factor", out["stability"])
        self.assertIn("style_hints", out["stability"])
        self.assertIn("style_hints", out)
        self.assertEqual(out["style_hints"].get("writing_style"), "concise")

        # With high damping, fusion_score should move toward 0.5 from 0.9
        self.assertLess(out["fusion_score"], 0.90)
        self.assertGreater(out["fusion_score"], 0.45)

    def test_apply_is_safe_without_fusion_score(self):
        hub = DummyMemoryHub()
        hub.traces = [{"payload": {"type": "drift_report", "drift_score": 0.2, "drift_tags": []}}]
        stab = FusionStabilizer(memory_hub=hub, safety_monitor=AllowSafety())

        out = stab.apply_to_fusion_result({"final_message": "ok"})
        self.assertIn("stability", out)
        self.assertEqual(out["final_message"], "ok")


if __name__ == "__main__":
    unittest.main()
