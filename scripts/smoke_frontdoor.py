# scripts/smoke_frontdoor.py
from __future__ import annotations

# --- PATH FIX: allow `import ssn...` when running `python3 scripts/...` ---
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # /workspaces/SSN
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ------------------------------------------------------------------------

import os
import json

from ssn.runtime.runtime_builder import SSNRuntimeBuilder
from ssn.interfaces.front_door import handle_user_message


def j(x):
    print(json.dumps(x, indent=2, ensure_ascii=False))


def main():
    mk = os.getenv("SSN_MASTER_KEY")  # set this in your environment for OWNER tests

    rt = SSNRuntimeBuilder.build_default(default_role="GUEST", output_mode="full")
    orch = rt.orchestrator
    gw = rt.gateway

    print("\n[1] Wiring checks")
    reg_from_orch = getattr(orch, "tools", None) or getattr(orch, "tool_registry", None)
    reg_from_gateway = gw.deps.get("tool_registry")
    print("registry(orchestrator) is registry(gateway.deps):", reg_from_orch is reg_from_gateway)

    print("\n[2] FrontDoor GUEST chat (LLM-only route)")
    out = handle_user_message(
        "Hello SIONA. Briefly explain yourself.",
        {"orchestrator": orch, "tool_registry": reg_from_orch},
        {},
    )
    j(out)

    print("\n[3] FrontDoor offline research gate (should degrade, no web)")
    out = handle_user_message(
        "Research the latest Tesla earnings and cite sources.",
        {"orchestrator": orch, "tool_registry": reg_from_orch},
        {"offline": True},
    )
    j(out)

    if mk:
        print("\n[4] FrontDoor OWNER knowledge search (role derived from master key)")
        out = handle_user_message(
            "knowledge: bootstrap",
            {"orchestrator": orch, "tool_registry": reg_from_orch},
            {"meta": {"master_key": mk}},
        )
        j(out)

        print("\n[5] Interface sense_tick (OWNER-only) via AgentShell event")
        r = rt.shell.handle_event(
            {"type": "sense_tick", "context": {"max_events": 5}, "meta": {"master_key": mk}}
        )
        j({"ok": r.ok, "action": r.action, "role": r.role, "data": r.data, "error": (r.error.__dict__ if r.error else None)})

        print("\n[6] Interface world (OWNER-only) via AgentShell event")
        r = rt.shell.handle_event(
            {"type": "world", "context": {"max_entities": 5, "max_events": 5}, "meta": {"master_key": mk}}
        )
        j({"ok": r.ok, "action": r.action, "role": r.role, "data": r.data, "error": (r.error.__dict__ if r.error else None)})

    else:
        print("\n[4-6] OWNER smoke skipped (SSN_MASTER_KEY not set). Set SSN_MASTER_KEY to test OWNER flows.")


if __name__ == "__main__":
    main()
