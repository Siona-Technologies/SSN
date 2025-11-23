from ssn.core.fusion_engine import FusionEngine

fusion = FusionEngine()

print("=== OWNER: Explain something ===")
print(fusion.fuse("SSN, explain fusion.", role="OWNER"))

print("\n=== SENSOR INPUT: numeric ===")
print(fusion.fuse(42, role="OWNER"))

print("\n=== GUEST user ===")
print(fusion.fuse("Hello what can you do?", role="GUEST"))
