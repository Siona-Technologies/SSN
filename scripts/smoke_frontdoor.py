# scripts/smoke_frontdoor.py
from __future__ import annotations

# --- PATH FIX: allow `import ssn...` when running `python3 scripts/...` ---
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# ------------------------------------------------------------------------

import os
import json
from typing import Any

from ssn.runtime.runtime_builder import SSNRuntimeBuilder
from ssn.interfaces.front_door import handle_user_message


def j(x: Any) -> None:
    print(json.dumps(x, indent=2, ensure_ascii=False, default=str))


def _json_str(x: Any) -> str:
    try:
        return json.dumps(x, ensure_ascii=False, default=str)
    except Exception:
        return str(x)


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


_SECRET_KEY_NAMES = {"master_key", "ssn_master_key"}


def _contains_exact_secret_key(obj: Any) -> bool:
    """
    Returns True if obj contains a dict key exactly equal to 'master_key' or 'ssn_master_key'.
    This avoids false positives like 'master_key_score'.
    """
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).strip().lower() in _SECRET_KEY_NAMES:
                return True
            if _contains_exact_secret_key(v):
                return True
        return False
    if isinstance(obj, list):
        return any(_contains_exact_secret_key(v) for v in obj)
    return False


def _assert_no_secret_leak(obj: Any) -> None:
    _assert(not _contains_exact_secret_key(obj), "Secret leak: exact secret key name found in output.")


def _assert_no_secret_value_leak(obj: Any, *, mk: str | None) -> None:
    """
    Optional: ensure the master key VALUE is not present anywhere in output.
    (This is safe for your current tests; avoid using this if you ever echo mk in prompts.)
    """
    if not mk:
        return
    s = _json_str(obj)
    _assert(mk not in s, "Secret leak: master key VALUE appears in output.")


def main() -> None:
    mk = os.getenv("SSN_MASTER_KEY")  # set env for OWNER tests

    rt = SSNRuntimeBuilder.build_default(default_role="GUEST", output_mode="full")
    orch = rt.orchestrator
    gw = rt.gateway

    reg_from_orch = getattr(orch, "tools", None) or getattr(orch, "tool_registry", None)
    reg_from_gateway = gw.deps.get("tool_registry")

    print("\n[1] Wiring checks")
    print("registry(orchestrator) is registry(gateway.deps):", reg_from_orch is reg_from_gateway)
    _assert(reg_from_orch is not None, "Orchestrator ToolRegistry missing.")
    _assert(reg_from_orch is reg_from_gateway, "Split-brain: gateway.deps.tool_registry is not orchestrator.tools")

    print("\n[2] FrontDoor GUEST chat (LLM-only route, deterministic offline)")
    out = handle_user_message(
        "Hello SIONA. Briefly explain yourself.",
        {"orchestrator": orch, "tool_registry": reg_from_orch, "gateway": gw},
        {"offline": True},  # deterministic
    )
    j(out)
    _assert(isinstance(out, dict) and isinstance(out.get("answer"), str) and out["answer"].strip(), "No answer returned.")
    _assert_no_secret_leak(out)
    _assert_no_secret_value_leak(out, mk=mk)

    print("\n[3] FrontDoor GUEST promote (must deny)")
    out = handle_user_message(
        "promote: store this fact: test",
        {"orchestrator": orch, "tool_registry": reg_from_orch, "gateway": gw},
        {"offline": True, "allow_tools": True},
    )
    j(out)
    _assert("owner-only" in (out.get("answer", "").lower()), "GUEST promote should be denied.")
    _assert_no_secret_leak(out)
    _assert_no_secret_value_leak(out, mk=mk)

    if not mk:
        print("\n[4-8] OWNER smoke skipped (SSN_MASTER_KEY not set). Set SSN_MASTER_KEY to test OWNER flows.")
        return

    print("\n[4] FrontDoor OWNER knowledge search (role derived from master key)")
    out = handle_user_message(
        "knowledge: bootstrap",
        {"orchestrator": orch, "tool_registry": reg_from_orch, "gateway": gw},
        {"offline": True, "allow_tools": True, "meta": {"master_key": mk}},
    )
    j(out)
    _assert(out.get("session_state", {}).get("role") == "OWNER", "Expected OWNER role in session_state.")
    _assert_no_secret_leak(out)
    _assert_no_secret_value_leak(out, mk=mk)

    print("\n[5] FrontDoor OWNER research (offline + strict=True + allow_degraded=False) must BLOCK")
    out = handle_user_message(
        "What is the speed of light? Provide citations.",
        {"orchestrator": orch, "tool_registry": reg_from_orch, "gateway": gw},
        {
            "offline": True,
            "strict": True,
            "allow_degraded": False,
            "allow_tools": True,
            "allow_research": True,
            "meta": {"master_key": mk},
        },
    )
    j(out)
    _assert(
        "offline" in _json_str(out).lower()
        or "blocked" in (out.get("answer", "").lower())
        or "degraded" in _json_str(out).lower(),
        "Expected offline research to be blocked when allow_degraded=False.",
    )
    _assert_no_secret_leak(out)
    _assert_no_secret_value_leak(out, mk=mk)

    print("\n[6] FrontDoor OWNER research (offline + strict=True + allow_degraded=True) should RUN deterministically")
    out = handle_user_message(
        "What is the speed of light? Provide citations.",
        {"orchestrator": orch, "tool_registry": reg_from_orch, "gateway": gw},
        {
            "offline": True,
            "strict": True,
            "allow_degraded": True,
            "allow_tools": True,
            "allow_research": True,
            "meta": {"master_key": mk},
        },
    )
    j(out)
    _assert(isinstance(out.get("answer"), str) and out["answer"].strip(), "Research answer missing.")
    _assert(isinstance(out.get("citations", []), list), "citations should be a list (even if empty).")
    _assert_no_secret_leak(out)
    _assert_no_secret_value_leak(out, mk=mk)

    print("\n[7] Interface sense_tick (OWNER-only) via AgentShell event")
    r = rt.shell.handle_event({"type": "sense_tick", "context": {"max_events": 5}, "meta": {"master_key": mk}})
    env = {"ok": r.ok, "action": r.action, "role": r.role, "data": r.data, "error": (r.error.__dict__ if r.error else None)}
    j(env)
    _assert(r.ok is True, "sense_tick should succeed for OWNER.")
    _assert_no_secret_leak(env)
    _assert_no_secret_value_leak(env, mk=mk)

    print("\n[8] Interface world (OWNER-only) via AgentShell event")
    r = rt.shell.handle_event({"type": "world", "context": {"max_entities": 5, "max_events": 5}, "meta": {"master_key": mk}})
    env = {"ok": r.ok, "action": r.action, "role": r.role, "data": r.data, "error": (r.error.__dict__ if r.error else None)}
    j(env)
    _assert(r.ok is True, "world should succeed for OWNER.")
    _assert_no_secret_leak(env)
    _assert_no_secret_value_leak(env, mk=mk)

    print("\nALL SMOKE TESTS PASSED.")


if __name__ == "__main__":
    main()
