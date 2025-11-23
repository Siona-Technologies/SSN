"""
Test Orchestrator (Phase 3.4 – Full Hybrid Brain)

Covers:
- OWNER (correct master key)
- OWNER (wrong key)
- GUEST behavior
- Full vs minimal output modes
- Language, numeric, and byte-stream inputs
"""

from ssn.core.orchestrator import Orchestrator


# ============================================================
# 1. FULL OUTPUT MODE (detailed introspection)
# ============================================================
print("\n============================")
print("TEST 1 — OWNER (Correct Key, Full Mode)")
print("============================")

orch_full = Orchestrator(output_mode="full")

result_owner_full = orch_full.handle_request(
    master_key="Warlord101",
    user_input="Explain the SSN hybrid brain.",
    context={"device_id": "laptop-1"}
)

print(result_owner_full)



# ============================================================
# 2. OWNER — WRONG KEY
# ============================================================
print("\n============================")
print("TEST 2 — OWNER (Wrong Key)")
print("============================")

result_wrong_key = orch_full.handle_request(
    master_key="WRONG_KEY",
    user_input="Explain the SSN hybrid brain.",
)

print(result_wrong_key)



# ============================================================
# 3. OWNER – NUMERIC SENSOR INPUT
# ============================================================
print("\n============================")
print("TEST 3 — OWNER (Sensor Input)")
print("============================")

result_numeric = orch_full.handle_request(
    master_key="Warlord101",
    user_input=42,                # numeric sensor-style data
)

print(result_numeric)



# ============================================================
# 4. OWNER – BYTE STREAM INPUT
# ============================================================
print("\n============================")
print("TEST 4 — OWNER (Bytes Stream)")
print("============================")

result_bytes = orch_full.handle_request(
    master_key="Warlord101",
    user_input=b"\x08\xFF\x01",
)

print(result_bytes)



# ============================================================
# 5. GUEST — TEXT INPUT
# ============================================================
print("\n============================")
print("TEST 5 — GUEST Behaviour")
print("============================")

result_guest = orch_full.handle_request(
    master_key=None,
    user_input="Hello SSN, what can you do?",
)

print(result_guest)



# ============================================================
# 6. MINIMAL OUTPUT MODE (production-like)
# ============================================================
print("\n============================")
print("TEST 6 — Minimal Mode (Production Style)")
print("============================")

orch_minimal = Orchestrator(output_mode="minimal")

result_minimal = orch_minimal.handle_request(
    master_key="Warlord101",
    user_input="Give me a summary of fusion cognition.",
)

print(result_minimal)
