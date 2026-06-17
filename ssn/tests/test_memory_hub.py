# ssn/tests/test_memory_hub.py

from ssn.memory.memory_hub import MemoryHub


if __name__ == "__main__":
    hub = MemoryHub()

    print("=== TEST 1: Semantic facts ===")
    hub.remember_fact("samson.favorite_language", "Python")
    print("Fact:", hub.recall_fact("samson.favorite_language"))
    print("All facts:", hub.recall_all_facts())

    print("\n=== TEST 2: Profile preferences & behaviors via helper ===")
    hub.remember_preference("tone", "friendly")
    hub.remember_behavior("decision_speed", "fast")
    print("Profile:", hub.recall_profile())

    print("\n=== TEST 3: Episodic events ===")
    hub.log_event(
        event_type="test_event",
        actor="Samson",
        details={"note": "memory hub sanity check"},
    )
    recent = hub.recall_recent_events(limit=3)
    print("Recent events:", recent)

    print("\n=== TEST 4: Interaction logging ===")
    fake_routed = {
        "mode": "deep",
        "mode_locked": False,
        "auto_message": "test auto",
        "result": {
            "engine": "llm-deep",
            "llm": {"reply": "dummy"},
            "note": "test note",
        },
    }
    fake_fusion = {
        "role": "OWNER",
        "mode": "hybrid",
        "fusion_score": 0.75,
        "cognition_llm": {},
        "perception_snn": {},
        "final_message": "dummy fusion",
    }

    hub.log_interaction(
        role="OWNER",
        user_input="Testing full memory integration.",
        brain_mode="deep",
        routed_engine=fake_routed,
        fusion_result=fake_fusion,
    )
    print("Recent after interaction:", hub.recall_recent_events(limit=5))

    print("\n=== TEST 5: Auto-index simple text (favorite color) ===")
    text = "By the way, my favorite color is blue."
    hub.auto_index_from_text("OWNER", text)
    print("Favorite color fact:", hub.recall_fact("samson.favorite_color"))
    print("Profile now:", hub.recall_profile())
