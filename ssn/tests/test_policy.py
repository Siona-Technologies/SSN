from ssn.policy.policy_engine import PolicyEngine

engine = PolicyEngine()

print("=== OWNER TEST ===")
print(engine.validate_action("OWNER", "access_full_memory"))

print("=== USER TEST ===")
print(engine.validate_action("STANDARD_USER", "access_full_memory"))

print("=== WORLD LAW TEST ===")
print(engine.validate_action("OWNER", "bypass_global_security"))
