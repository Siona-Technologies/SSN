# ssn/tests/test_memory_orchestrator_integration.py

from ssn.core.orchestrator import Orchestrator

MASTER_KEY = "Warlord101"  # must match the one you initialized

print("=== ORCH + MEMORY INTEGRATION TEST ===")

# Full debug/introspection mode
orch_full = Orchestrator(output_mode="full")

print("\n--- 1) OWNER: rich cognitive request ---")
result_owner = orch_full.handle_request(
    master_key=MASTER_KEY,
    user_input="SSN, explain how your memory system works and keep learning my preferences.",
    context={
        "device_id": "sibona-laptop",
        "session_id": "test-session-001",
    },
)
print(result_owner)

# Minimal mode — production-style
orch_minimal = Orchestrator(output_mode="minimal")

print("\n--- 2) OWNER: minimal mode call ---")
result_min = orch_minimal.handle_request(
    master_key=MASTER_KEY,
    user_input="Summarize what you remember from this interaction.",
    context={},
)
print(result_min)

print("\n--- 3) GUEST: blocked or restricted ---")
result_guest = orch_minimal.handle_request(
    master_key="WRONG_KEY",
    user_input="Hello, what can you do?",
    context={},
)
print(result_guest)
