from ssn.core.snn_engine import SNNEngine

engine = SNNEngine()

print("\n=== Test 1: Numeric events ===")
print(engine.process_event_stream([1, 2, 3, 4]))

print("\n=== Test 2: String events ===")
print(engine.process_event_stream("hello spikes"))

print("\n=== Test 3: Bytes events ===")
print(engine.process_event_stream(b"\x10\x20\x30\x40"))

print("\n=== Test 4: Empty input ===")
print(engine.process_event_stream([]))
