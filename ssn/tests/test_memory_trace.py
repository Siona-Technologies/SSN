# ssn/tests/test_memory_trace.py

from ssn.memory.memory_hub import MemoryHub

hub = MemoryHub()

print("=== TRACE TEST 1: Raw episodic events ===")
hub.log_event(
    event_type="system_boot",
    actor="System",
    details={"message": "SSN booted for trace test"},
)
hub.log_event(
    event_type="config_change",
    actor="Samson",
    details={"message": "Updated SSN brain mode defaults"},
)
events = hub.recall_recent_events(limit=5)
print("Recent events:", events)

print("\n=== TRACE TEST 2: Interaction trace ===")
fake_routed = {
    "mode": "hybrid",
    "mode_locked": False,
    "auto_message": "trace-test",
    "result": {
        "engine": "fusion",
        "note": "Trace test routing",
    },
}
fake_fusion = {
    "role": "OWNER",
    "mode": "hybrid",
    "fusion_score": 0.88,
    "cognition_llm": {},
    "perception_snn": {},
    "final_message": "Trace test fusion result",
}

hub.log_interaction(
    role="OWNER",
    user_input="Log this interaction for trace analysis.",
    brain_mode="hybrid",
    routed_engine=fake_routed,
    fusion_result=fake_fusion,
)
print("Recent after interaction:", hub.recall_recent_events(limit=10))

print("\n=== TRACE TEST 3: Search in episodic memory ===")
matches = hub.search_events("trace")
print("Search 'trace' matches:", matches)
