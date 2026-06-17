# ssn/tests/test_memory_profile.py

from ssn.memory.memory_hub import MemoryHub


if __name__ == "__main__":
    hub = MemoryHub()

    print("=== PROFILE TEST 1: Basic preferences ===")
    hub.remember_preference("ui_theme", "dark")
    hub.remember_preference("response_tone", "precise")
    print("Profile after preferences:", hub.recall_profile())

    print("\n=== PROFILE TEST 2: Behavioral patterns ===")
    hub.remember_behavior("decision_speed", "fast")
    hub.remember_behavior("writing_style", "technical-but-clear")
    print("Profile after behaviors:", hub.recall_profile())

    print("\n=== PROFILE TEST 3: Combined snapshot ===")
    profile = hub.recall_profile()
    print("Preferences:", profile.get("preferences"))
    print("Behaviors:", profile.get("behaviors"))
