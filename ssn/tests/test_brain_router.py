from ssn.core.brain_router import BrainRouter

router = BrainRouter()

print("\n=== OWNER: natural language ===")
print(router.route("OWNER", "Explain the SSN brain."))

print("\n=== OWNER: numeric sensor data ===")
print(router.route("OWNER", 42))

print("\n=== OWNER: bytes stream ===")
print(router.route("OWNER", b'\x01\x02\x03'))

print("\n=== GUEST: restricted ===")
print(router.route("GUEST", "Hello, what is SSN?"))
