from ssn.core.language_engine import LanguageEngine


if __name__ == "__main__":
    engine = LanguageEngine()

    print("=== OWNER TEST ===")
    owner_result = engine.generate_reply(
        prompt="SSN, explain your current phase.",
        role="OWNER",
        context={"phase": "3.1"}
    )
    print(owner_result["text"])
    print(owner_result["meta"])
    print()

    print("=== GUEST TEST ===")
    guest_result = engine.generate_reply(
        prompt="Hello, what is SSN?",
        role="GUEST"
    )
    print(guest_result["text"])
    print(guest_result["meta"])
