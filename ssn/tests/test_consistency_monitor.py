# ssn/tests/test_consistency_monitor.py

from ssn.core.consistency_monitor import ConsistencyMonitor



if __name__ == "__main__":
    class DummyMemoryHub:
        def __init__(self, traces):
            self._traces = traces
            self.writes = 0

        def get_recent_traces(self, limit=30):
            return self._traces[:limit]

        def write_trace(self, source, payload, bounded=False):
            self.writes += 1


    class AllowSafety:
        def allow_internal_reflection(self):
            return True


    class DenySafety:
        def allow_internal_reflection(self):
            return False


    def test_consistency_monitor_aborts_on_safety_denied():
        hub = DummyMemoryHub([])
        mon = ConsistencyMonitor(hub, DenySafety())
        out = mon.evaluate_recent()
        assert out["status"] == "aborted"
        assert hub.writes == 0


    def test_consistency_monitor_writes_once_and_bounds_score():
        traces = [
            {"payload": {"brain_mode": "fast", "reasoning_depth": 1, "tags": []}},
            {"payload": {"brain_mode": "deep", "reasoning_depth": 4, "tags": []}},
            {"payload": {"brain_mode": "fast", "reasoning_depth": 2, "safety_flag": True}},
        ]
        hub = DummyMemoryHub(traces)
        mon = ConsistencyMonitor(hub, AllowSafety())
        out = mon.evaluate_recent(trace_limit=10, write_trace=True)

        assert out["status"] == "completed"
        assert 0.0 <= out["drift_score"] <= 1.0
        assert isinstance(out["drift_tags"], list)
        assert hub.writes == 1
