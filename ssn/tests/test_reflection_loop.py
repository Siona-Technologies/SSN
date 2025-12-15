# ssn/tests/test_reflection_loop.py

from ssn.runtime.reflection_loop import ReflectionLoop


class DummyMemoryHub:
    def __init__(self):
        self.traces_written = 0

    def get_recent_traces(self, limit=5):
        return []

    def get_recent_episodic(self, limit=3):
        return []

    def write_trace(self, source, payload, bounded=False):
        self.traces_written += 1


class DummySafetyMonitor:
    def allow_internal_reflection(self):
        return True


class DummySelfReflection:
    def inspect(self, trace_memory, episodic_memory):
        return {"note": "ok"}


def test_reflection_loop_runs_once():
    loop = ReflectionLoop(
        memory_hub=DummyMemoryHub(),
        safety_monitor=DummySafetyMonitor(),
        self_reflection=DummySelfReflection(),
    )

    result = loop.run_once()
    assert result["status"] == "completed"


def test_reflection_loop_single_memory_write():
    hub = DummyMemoryHub()
    loop = ReflectionLoop(
        memory_hub=hub,
        safety_monitor=DummySafetyMonitor(),
        self_reflection=DummySelfReflection(),
    )

    loop.run_once()
    assert hub.traces_written == 1
