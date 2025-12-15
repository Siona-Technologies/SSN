# ssn/tests/test_phase38_fusion_stabilizer_no_drift_regression.py

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


class TestPhase38FusionStabilizerNoDriftRegression(unittest.TestCase):

    def test_no_drift_report_means_no_baseline_damping(self):
        hub = DummyMemoryHub()
        # Provide traces that are NOT drift_report
        hub.traces = [
            {"payload": {"type": "reflection_summary", "insights": [{"note": "ok"}]}},
            {"payload": {"type": "preference_update", "stable_candidates": [{"key": "writing_style", "value": "concise", "confidence": 0.8}]}},
        ]

        stab = FusionStabilizer(memory_hub=hub, safety_monitor=AllowSafety())
        adj = stab.compute()

        self.assertEqual(adj.drift_score, 0.0)
        self.assertEqual(adj.damping_factor, 0.0)

        out = stab.apply_to_fusion_result({"fusion_score": 0.9})
        # score should remain unchanged because damping_factor is 0.0
        self.assertAlmostEqual(out["fusion_score"], 0.9, places=9)


if __name__ == "__main__":
    unittest.main()
