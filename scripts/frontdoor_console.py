import os
from ssn.core.orchestrator import Orchestrator
from ssn.interfaces.front_door import handle_user_message

orch = Orchestrator(output_mode="full")
deps = {"orchestrator": orch}

print("SSN Console (FrontDoor). Type 'exit' to quit.\n")

turn = 0
while True:
    try:
        msg = input("you> ").strip()
    except EOFError:
        break
    if msg.lower() in ("exit", "quit"):
        break
    if not msg:
        continue

    turn += 1
    ctx = {
        "session_id": "console",
        "turn_id": turn,
        "offline": True,
        "allow_tools": False,
        "allow_research": False,
        "meta": {"master_key": os.environ.get("SSN_MASTER_KEY", "")},
    }
    out = handle_user_message(msg, deps, ctx)
    print("ssn>", out.get("answer", ""))
