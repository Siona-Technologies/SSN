# ssn/tests/test_phase37_suggestion_engine.py

import unittest

from ssn.core.suggestion_engine import SuggestionEngine


class DummyMemoryHub:
    def __init__(self):
        self.traces = []
        self.writes = []

    def get_recent_traces(self, limit=120):
        return self.traces[:limit]

    def write_trace(self, source, payload, bounded=False):
        self.writes.append({"source": source, "payload": payload, "bounded": bounded})


class AllowSafety:
    def allow_internal_reflection(self):
        return True


class DenySafety:
    def allow_internal_reflection(self):
        return False


class TestPhase37SuggestionEngine(unittest.TestCase):

    def test_suggestion_engine_aborts_on_safety_denied(self):
        hub = DummyMemoryHub()
        eng = SuggestionEngine(hub, DenySafety())
        out = eng.run_once()
        self.assertEqual(out["status"], "aborted")
        self.assertEqual(len(hub.writes), 0)

    def test_suggestion_engine_writes_once_and_is_advisory(self):
        hub = DummyMemoryHub()
        # Provide drift + consolidation + prefs so suggestions appear
        hub.traces = [
            {"payload": {"type": "drift_report", "drift_score": 0.65, "drift_tags": ["mode_oscillation"]}},
            {"payload": {"type": "consolidation_summary", "drift": {"drift_ok_for_promotion": False}, "promotion_candidates": [{"fact": "x"}]}},
            {"payload": {"type": "preference_update", "stable_candidates": [{"key": "writing_style", "value": "concise", "confidence": 0.75}]}},
        ]

        eng = SuggestionEngine(hub, AllowSafety())
        out = eng.run_once(write_trace=True)

        self.assertEqual(out["status"], "completed")
        self.assertTrue(out["requires_owner_ack"])
        self.assertEqual(len(hub.writes), 1)

        payload = hub.writes[0]["payload"]
        self.assertEqual(payload.get("type"), "suggestion_packet")
        self.assertTrue(payload.get("requires_owner_ack"))
        self.assertIsInstance(payload.get("suggestions", []), list)
        self.assertTrue(len(payload["suggestions"]) >= 1)

        # Ensure no action scope appears
        for s in payload["suggestions"]:
            self.assertNotEqual(s.get("scope"), "external_action")


if __name__ == "__main__":
    unittest.main()
