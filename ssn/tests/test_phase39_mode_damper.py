# ssn/tests/test_phase39_mode_damper.py

import unittest

from ssn.core.mode_damper import ModeDamper


class DummyMemoryHub:
    def __init__(self):
        self.traces = []

    def get_recent_traces(self, limit=120):
        return self.traces[:limit]


class AllowSafety:
    def allow_internal_reflection(self):
        return True


class TestPhase39ModeDamper(unittest.TestCase):

    def test_damps_to_hybrid_on_high_drift(self):
        hub = DummyMemoryHub()
        hub.traces = [{"payload": {"type": "drift_report", "drift_score": 0.75, "drift_tags": []}}]
        damper = ModeDamper(memory_hub=hub, safety_monitor=AllowSafety())

        d = damper.damp_mode("deep")
        self.assertEqual(d.selected_mode, "hybrid")
        self.assertTrue(d.damped)

    def test_respects_original_on_low_drift(self):
        hub = DummyMemoryHub()
        hub.traces = [{"payload": {"type": "drift_report", "drift_score": 0.10, "drift_tags": []}}]
        damper = ModeDamper(memory_hub=hub, safety_monitor=AllowSafety())

        d = damper.damp_mode("deep")
        self.assertEqual(d.selected_mode, "deep")
        self.assertFalse(d.damped)

    def test_damps_on_mode_oscillation_with_moderate_drift(self):
        hub = DummyMemoryHub()
        hub.traces = [{"payload": {"type": "drift_report", "drift_score": 0.45, "drift_tags": ["mode_oscillation"]}}]
        damper = ModeDamper(memory_hub=hub, safety_monitor=AllowSafety())

        d = damper.damp_mode("fast")
        self.assertEqual(d.selected_mode, "hybrid")
        self.assertTrue(d.damped)


if __name__ == "__main__":
    unittest.main()
