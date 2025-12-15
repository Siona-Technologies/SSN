# ssn/tests/test_phase38_hybrid_pipeline_regression.py

import unittest

from ssn.runtime.reflection_loop import ReflectionLoop
from ssn.core.consistency_monitor import ConsistencyMonitor
from ssn.memory.consolidation import MemoryConsolidator
from ssn.memory.preference_memory import PreferenceStabilizer
from ssn.core.suggestion_engine import SuggestionEngine
from ssn.core.fusion_engine import FusionEngine


class DummyMemoryHub:
    """
    Stores traces so Phase 3.7 modules + Phase 3.8 FusionStabilizer can read them.
    """
    def __init__(self):
        self.traces = []
        self.episodic = [{"event": "boot"}, {"event": "session_start"}]
        self.writes = []

    def get_recent_traces(self, limit=200):
        # newest-first
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
        return {"note": "prefer concise outputs"}


class TestPhase38HybridPipelineRegression(unittest.TestCase):

    def test_phase38_hybrid_pipeline_with_fusion_stabilization(self):
        hub = DummyMemoryHub()
        safety = AllowSafety()

        # Phase 3.7 chain
        ReflectionLoop(hub, safety, DummySelfReflection()).run_once()
        ConsistencyMonitor(hub, safety).evaluate_recent(trace_limit=60, write_trace=True)
        MemoryConsolidator(hub, safety).run_once(trace_limit=80, episodic_limit=10, write_trace=True)
        PreferenceStabilizer(hub, safety).run_once(trace_limit=120, write_trace=True)
        SuggestionEngine(hub, safety).run_once(trace_limit=150, write_trace=True)

        # Now fuse with stabilization present (FusionEngine gets memory_hub + safety_monitor)
        fusion = FusionEngine(memory_hub=hub, safety_monitor=safety)
        out = fusion.fuse("Test hybrid fusion stability", role="OWNER", context={}, mode="deep")

        self.assertIn("stability", out)  # stabilization overlay should exist
        self.assertIn("fusion_score", out)
        self.assertGreaterEqual(out["fusion_score"], 0.0)
        self.assertLessEqual(out["fusion_score"], 1.0)

        # Ensure advisory hints are present (if preference candidates exist)
        self.assertIn("style_hints", out)
        # Not strictly required, but typically present with our DummySelfReflection
        # so we check it's a dict at least:
        self.assertIsInstance(out["style_hints"], dict)

        # Ensure final_message reflects stabilized fusion_score
        self.assertIn(str(out["fusion_score"]), out["final_message"])


if __name__ == "__main__":
    unittest.main()
