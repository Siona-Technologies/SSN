# ssn/tests/test_phase37_pipeline_regression.py

import unittest

from ssn.runtime.reflection_loop import ReflectionLoop
from ssn.core.consistency_monitor import ConsistencyMonitor
from ssn.memory.consolidation import MemoryConsolidator
from ssn.memory.preference_memory import PreferenceStabilizer
from ssn.core.suggestion_engine import SuggestionEngine


class DummyMemoryHub:
    """
    In-memory hub for Phase 3.7 regression.
    We store writes as traces so downstream steps can read them.
    """
    def __init__(self):
        self.traces = []
        self.episodic = [{"event": "boot"}, {"event": "session_start"}]
        self.writes = []

    def get_recent_traces(self, limit=200):
        # Return newest-first (common pattern), but regression is robust either way.
        return list(reversed(self.traces))[:limit]

    def get_recent_episodic(self, limit=10):
        return self.episodic[:limit]

    def write_trace(self, source, payload, bounded=False):
        item = {"source": source, "payload": payload, "bounded": bounded}
        self.writes.append(item)
        self.traces.append(item)


class AllowSafety:
    def allow_internal_reflection(self):
        return True


class DummySelfReflection:
    def inspect(self, trace_memory, episodic_memory):
        # produce a preference hint twice across loop steps to enable stabilization
        return {"note": "prefer concise outputs"}


class TestPhase37PipelineRegression(unittest.TestCase):

    def test_phase37_pipeline_end_to_end(self):
        hub = DummyMemoryHub()
        safety = AllowSafety()
        self_ref = DummySelfReflection()

        # 1) Reflection
        loop = ReflectionLoop(hub, safety, self_ref)
        out1 = loop.run_once()
        self.assertEqual(out1["status"], "completed")

        # 2) Drift/Consistency
        mon = ConsistencyMonitor(hub, safety)
        out2 = mon.evaluate_recent(trace_limit=50, write_trace=True)
        self.assertEqual(out2["status"], "completed")

        # 3) Consolidation
        cons = MemoryConsolidator(hub, safety)
        out3 = cons.run_once(trace_limit=80, episodic_limit=10, write_trace=True)
        self.assertEqual(out3["status"], "completed")

        # 4) Preference stabilization
        pref = PreferenceStabilizer(hub, safety)
        out4 = pref.run_once(trace_limit=120, write_trace=True)
        self.assertEqual(out4["status"], "completed")

        # 5) Suggestions
        sug = SuggestionEngine(hub, safety)
        out5 = sug.run_once(trace_limit=150, write_trace=True)
        self.assertEqual(out5["status"], "completed")
        self.assertTrue(out5["requires_owner_ack"])

        # Assertions: bounded writes and expected payload types exist
        self.assertGreaterEqual(len(hub.writes), 5)
        for w in hub.writes[-5:]:
            self.assertTrue(w["bounded"])

        types = [w["payload"].get("type") for w in hub.traces]
        self.assertIn("reflection_summary", types)
        self.assertIn("drift_report", types)
        self.assertIn("consolidation_summary", types)
        self.assertIn("preference_update", types)
        self.assertIn("suggestion_packet", types)


if __name__ == "__main__":
    unittest.main()
