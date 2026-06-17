from ssn.core.brain_modes import ModeManager


if __name__ == "__main__":
    m = ModeManager()

    print("=== Initial state ===")
    print("Mode:", m.get_mode(), "Locked:", m.is_locked())
    print()

    print("=== Manual: Deep Reasoning Mode ===")
    print(m.manual_set_mode("deep", role="OWNER"))
    print("Current mode:", m.get_mode())
    print()

    print("=== Manual: Fast Reaction Mode ===")
    print(m.manual_set_mode("fast", role="OWNER"))
    print("Current mode:", m.get_mode())
    print()

    print("=== Lock mode ===")
    print(m.lock_mode(True))
    print("Locked:", m.is_locked())
    print()

    print("=== Auto: should try to go deep (but locked) ===")
    msg = m.auto_set_mode(
        role="OWNER",
        user_input="Explain the full SSN architecture with all layers."
    )
    print("Auto message:", msg)
    print("Mode still:", m.get_mode())
    print()

    print("=== Unlock mode ===")
    print(m.lock_mode(False))
    print("Locked:", m.is_locked())
    print()

    print("=== Auto: deep reasoning request ===")
    msg = m.auto_set_mode(
        role="OWNER",
        user_input="Explain the full SSN architecture with all layers."
    )
    print("Auto message:", msg)
    print("Mode now:", m.get_mode())
    print()

    print("=== Auto: short, urgent request (fast) ===")
    msg = m.auto_set_mode(
        role="OWNER",
        user_input="Quick status check, any anomaly?"
    )
    print("Auto message:", msg)
    print("Mode now:", m.get_mode())
    print()

    print("=== Guest behavior ===")
    msg = m.auto_set_mode(
        role="GUEST",
        user_input="Explain SSN."
    )
    print("Auto message:", msg)
    print("Mode now (still):", m.get_mode())
