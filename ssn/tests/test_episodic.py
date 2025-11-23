from ssn.memory.episodic_memory import EpisodicMemory

mem = EpisodicMemory()

print("Recording event...")
e = mem.record_event("test_event", "Samson", {"note": "first memory entry"})
print(e)

print("\nRecent events:")
print(mem.get_recent(1))

print("\nSearching for 'first':")
print(mem.search("first"))
