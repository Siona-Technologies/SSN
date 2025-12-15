# ssn/tests/test_phase37_memory_consolidation.py

import unittest

from ssn.memory.consolidation import MemoryConsolidator


class DummyMemoryHub:
    def __init__(self):
        self.traces = []
        self.episodic = []
        self.writes = []
        self.semantic_mutations = 0

    def get_recent_traces(self, limit=60):
        return self.traces[:limit]

    def get_recent_episodic(self, limit=10):
        return self.episodic[:limit]

    def write_trace(self, source, payload, bounded=False):
        self.writes.append({"source": source, "payload": payload, "bounded": bounded})

    # If consolidator accidentally calls semantic mutation, we can detect it
    def write_semantic(self, *args, **kwargs):
        self.semantic_mutations += 1


class AllowSafety:
    def allow_internal_reflection(self):
        return True


class DenySafety:
    def allow_internal_reflection(self):
        return False


class TestPhase37MemoryConsolidation(unittest.TestCase):

    def test_consolidation_aborts_on_safety_denied(self):
        hub = DummyMemoryHub()
        cons = MemoryConsolidator(hub, DenySafety())
        out = cons.run_once()
        self.assertEqual(out["status"], "aborted")
        self.assertEqual(len(hub.writes), 0)

    def test_consolidation_writes_once_bounded_and_no_semantic_mutation(self):
        hub = DummyMemoryHub()
        # reflection summaries + drift reports
        hub.traces = [
            {"payload": {"type": "reflection_summary", "insights": [{"note": "prefer concise outputs"}, {"note": "prefer concise outputs"}]}},
            {"payload": {"type": "drift_report", "drift_score": 0.2, "drift_tags": []}},
            {"payload": {"type": "drift_report", "drift_score": 0.3, "drift_tags": ["mode_oscillation"]}},
        ]
        hub.episodic = [{"event": "x"}, {"event": "y"}]

        cons = MemoryConsolidator(hub, AllowSafety())
        out = cons.run_once(write_trace=True)

        self.assertEqual(out["status"], "completed")
        self.assertEqual(len(hub.writes), 1)
        self.assertEqual(hub.writes[0]["source"], "memory_consolidator")
        self.assertTrue(hub.writes[0]["bounded"])

        payload = hub.writes[0]["payload"]
        self.assertEqual(payload.get("type"), "consolidation_summary")
        self.assertIn("promotion_candidates", payload)

        # Ensure we did not mutate semantic store automatically
        self.assertEqual(hub.semantic_mutations, 0)


if __name__ == "__main__":
    unittest.main()
