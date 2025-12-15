# ssn/tests/test_phase37_reflection_and_drift.py

import unittest

from ssn.runtime.reflection_loop import ReflectionLoop
from ssn.core.consistency_monitor import ConsistencyMonitor


class DummyMemoryHub:
    """
    Minimal contract required by ReflectionLoop + ConsistencyMonitor.
    Tracks writes so we can assert bounded behavior.
    """
    def __init__(self):
        self.traces = []
        self.episodic = []
        self.writes = []

    def get_recent_traces(self, limit=5):
        return self.traces[:limit]

    def get_recent_episodic(self, limit=3):
        return self.episodic[:limit]

    def write_trace(self, source, payload, bounded=False):
        self.writes.append({"source": source, "payload": payload, "bounded": bounded})


class AllowSafetyMonitor:
    def allow_internal_reflection(self):
        return True


class DenySafetyMonitor:
    def allow_internal_reflection(self):
        return False


class DummySelfReflection:
    def __init__(self):
        self.calls = 0

    def inspect(self, trace_memory, episodic_memory):
        self.calls += 1
        return {"note": "ok", "call": self.calls}


class TestPhase37ReflectionAndDrift(unittest.TestCase):

    def test_reflection_loop_aborts_when_safety_denied(self):
        hub = DummyMemoryHub()
        loop = ReflectionLoop(
            memory_hub=hub,
            safety_monitor=DenySafetyMonitor(),
            self_reflection=DummySelfReflection(),
        )

        out = loop.run_once()
        self.assertEqual(out["status"], "aborted")
        self.assertEqual(len(hub.writes), 0)

    def test_reflection_loop_writes_once_bounded(self):
        hub = DummyMemoryHub()
        loop = ReflectionLoop(
            memory_hub=hub,
            safety_monitor=AllowSafetyMonitor(),
            self_reflection=DummySelfReflection(),
        )

        out = loop.run_once()
        self.assertEqual(out["status"], "completed")
        self.assertEqual(len(hub.writes), 1)
        self.assertEqual(hub.writes[0]["source"], "reflection_loop")
        self.assertTrue(hub.writes[0]["bounded"])

    def test_consistency_monitor_aborts_when_safety_denied(self):
        hub = DummyMemoryHub()
        mon = ConsistencyMonitor(memory_hub=hub, safety_monitor=DenySafetyMonitor())

        out = mon.evaluate_recent()
        self.assertEqual(out["status"], "aborted")
        self.assertEqual(len(hub.writes), 0)

    def test_consistency_monitor_writes_once_and_score_bounded(self):
        hub = DummyMemoryHub()
        # Feed traces with modes + depth + safety flag to ensure tags/metrics populate
        hub.traces = [
            {"payload": {"brain_mode": "fast", "reasoning_depth": 1}},
            {"payload": {"brain_mode": "deep", "reasoning_depth": 4}},
            {"payload": {"brain_mode": "fast", "reasoning_depth": 2, "safety_flag": True}},
        ]

        mon = ConsistencyMonitor(memory_hub=hub, safety_monitor=AllowSafetyMonitor())
        out = mon.evaluate_recent(trace_limit=30, write_trace=True)

        self.assertEqual(out["status"], "completed")
        self.assertGreaterEqual(out["drift_score"], 0.0)
        self.assertLessEqual(out["drift_score"], 1.0)
        self.assertIsInstance(out["drift_tags"], list)

        self.assertEqual(len(hub.writes), 1)
        self.assertEqual(hub.writes[0]["source"], "consistency_monitor")
        self.assertTrue(hub.writes[0]["bounded"])
        self.assertEqual(hub.writes[0]["payload"]["type"], "drift_report")


if __name__ == "__main__":
    unittest.main()

