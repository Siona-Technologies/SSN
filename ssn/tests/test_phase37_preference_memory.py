# ssn/tests/test_phase37_preference_memory.py

import unittest

from ssn.memory.preference_memory import PreferenceStabilizer


class DummyMemoryHub:
    def __init__(self):
        self.traces = []
        self.writes = []
        self.profile_mutations = 0

    def get_recent_traces(self, limit=80):
        return self.traces[:limit]

    def write_trace(self, source, payload, bounded=False):
        self.writes.append({"source": source, "payload": payload, "bounded": bounded})

    def update_profile(self, *args, **kwargs):
        self.profile_mutations += 1


class AllowSafety:
    def allow_internal_reflection(self):
        return True


class DenySafety:
    def allow_internal_reflection(self):
        return False


class TestPhase37PreferenceMemory(unittest.TestCase):

    def test_preference_stabilizer_aborts_on_safety_denied(self):
        hub = DummyMemoryHub()
        stab = PreferenceStabilizer(hub, DenySafety())
        out = stab.run_once()
        self.assertEqual(out["status"], "aborted")
        self.assertEqual(len(hub.writes), 0)

    def test_preference_stabilizer_extracts_repeated_preferences_and_writes_once(self):
        hub = DummyMemoryHub()
        # Two reflections repeating "prefer concise outputs"
        hub.traces = [
            {"payload": {"type": "reflection_summary", "insights": [{"note": "prefer concise outputs"}]}},
            {"payload": {"type": "reflection_summary", "insights": [{"note": "prefer concise outputs"}]}},
            {"payload": {"type": "drift_report", "drift_score": 0.2, "drift_tags": []}},  # ignored
        ]

        stab = PreferenceStabilizer(hub, AllowSafety())
        out = stab.run_once(write_trace=True)

        self.assertEqual(out["status"], "completed")
        self.assertEqual(len(hub.writes), 1)
        self.assertEqual(hub.writes[0]["source"], "preference_stabilizer")
        self.assertTrue(hub.writes[0]["bounded"])

        payload = hub.writes[0]["payload"]
        self.assertEqual(payload.get("type"), "preference_update")

        cands = payload.get("stable_candidates", [])
        self.assertTrue(isinstance(cands, list))
        # should contain writing_style=concise
        self.assertTrue(any(c.get("key") == "writing_style" and c.get("value") == "concise" for c in cands))

        # Ensure no profile mutation in Phase 3.7
        self.assertEqual(hub.profile_mutations, 0)


if __name__ == "__main__":
    unittest.main()
