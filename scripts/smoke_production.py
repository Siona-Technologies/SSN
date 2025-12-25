# scripts/smoke_production.py
"""
Production smoke test (Front Door + InterfaceGateway)

Goals:
- Build runtime via SSNRuntimeBuilder (canonical bootstrap)
- Call Front Door (production entrypoint)
- Call InterfaceGateway run_tool (internal entrypoint)
- Confirm single shared ToolRegistry wiring (no split brain)
- Stay deterministic in offline mode when SSN_OFFLINE=1

How to run:
  export PYTHONPATH=/workspaces/SSN
  export $(grep -v '^#' .env | xargs)
  python3 scripts/smoke_production.py

Optional env:
  SSN_MASTER_KEY=...     (enables OWNER smoke checks)
  SSN_OFFLINE=1          (forces offline behavior)
"""

from __future__ import annotations

# --- PATH FIX (keep) ---
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # /workspaces/SSN
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# -----------------------

import json
import os
from typing import Any, Dict

from ssn.runtime.runtime_builder import SSNRuntimeBuilder
from ssn.interfaces.front_door import handle_user_message
from ssn.interfaces.contracts import InterfaceRequest


def _pp(x: Any) -> str:
    return json.dumps(x, indent=2, ensure_ascii=False, sort_keys=True, default=str)


def _get_master_key() -> str:
    return (os.getenv("SSN_MASTER_KEY") or "").strip()


def _assert(cond: bool, msg: str) -> None:
    if not cond:
        raise AssertionError(msg)


def _forced_offline() -> bool:
    return os.getenv("SSN_OFFLINE") == "1"


def _gateway_run_tool(
    runtime,
    *,
    role: str,
    master_key: str,
    tool_name: str,
    args: Dict[str, Any],
) -> Dict[str, Any]:
    req = InterfaceRequest(
        action="run_tool",
        role=role,
        user_input="",
        context={"tool_name": tool_name, "args": args},
        meta={"master_key": master_key} if master_key else {},
    )
    resp = runtime.gateway.handle(req)
    return {
        "ok": bool(resp.ok),
        "action": resp.action,
        "role": resp.role,
        "data": resp.data,
        "error": (resp.error.__dict__ if resp.error else None),
    }


def main() -> int:
    print("\n=== ENV (smoke) ===")
    print("SSN_OFFLINE:", os.getenv("SSN_OFFLINE"))
    print("SSN_LIVE_SEARCH:", os.getenv("SSN_LIVE_SEARCH"))
    print("SSN_LIVE_STRICT:", os.getenv("SSN_LIVE_STRICT"))

    print("\n=== Building runtime via SSNRuntimeBuilder.build_default() ===")
    runtime = SSNRuntimeBuilder.build_default(default_role="GUEST", output_mode="full")

    deps = getattr(runtime.gateway, "deps", None) or {}
    orch = deps.get("orchestrator")
    reg_from_deps = deps.get("tool_registry")
    reg_from_orch = getattr(orch, "tools", None) if orch else None

    print("\n=== Wiring sanity ===")
    print("orchestrator:", type(orch).__name__ if orch else None)
    print("deps.tool_registry:", type(reg_from_deps).__name__ if reg_from_deps else None)
    print("orch.tools:", type(reg_from_orch).__name__ if reg_from_orch else None)

    if reg_from_deps is not None and reg_from_orch is not None:
        _assert(reg_from_deps is reg_from_orch, "Split-brain: deps['tool_registry'] is not orch.tools")

    master_key = _get_master_key()
    offline_forced = _forced_offline()

    # ------------------------------------------------------------
    # 1) Front Door baseline (respects SSN_OFFLINE)
    # ------------------------------------------------------------
    print("\n=== 1) Front Door baseline (respects SSN_OFFLINE) ===")
    ctx_guest = {
        "session_id": "smoke",
        "turn_id": "1",
        "offline": bool(offline_forced),
        "allow_tools": True,
        "allow_research": True,
    }
    out = handle_user_message("Hello SIONA. Give me a short status.", deps, ctx_guest)
    print(_pp(out))
    _assert(isinstance(out.get("answer"), str) and out["answer"].strip(), "FrontDoor did not return an answer string")

    # ------------------------------------------------------------
    # 2) GUEST research routing test (only meaningful when NOT offline)
    # ------------------------------------------------------------
    print("\n=== 2) Front Door research routing (GUEST) ===")
    if offline_forced:
        print("[SKIP] SSN_OFFLINE=1 forces offline; research routing is not expected to run.")
    else:
        ctx_guest_online = {
            "session_id": "smoke",
            "turn_id": "2",
            "offline": False,
            "allow_tools": True,
            "allow_research": True,
        }
        out2 = handle_user_message(
            "research What is the capital of Kenya? include citations",
            deps,
            ctx_guest_online,
        )
        print(_pp(out2))
        a2 = (out2.get("answer") or "")
        _assert(("Not authorized" in a2) or ("OWNER-only" in a2), "Expected GUEST research denial when online")

    # ------------------------------------------------------------
    # 3) InterfaceGateway run_tool (GUEST tools.public_list)
    #    NOTE: tools.list is OWNER-only by design in builtin_tools.py
    # ------------------------------------------------------------
    print("\n=== 3) InterfaceGateway run_tool (GUEST tools.public_list) ===")
    tool_list = _gateway_run_tool(runtime, role="GUEST", master_key="", tool_name="tools.public_list", args={})
    print(_pp(tool_list))

    d = tool_list.get("data") if isinstance(tool_list.get("data"), dict) else {}
    _assert(d.get("identity_verified") is False, f"Expected identity_verified=False, got: {_pp(d)}")
    _assert(d.get("role") == "GUEST", f"Expected role=GUEST, got: {_pp(d)}")
    _assert(d.get("allowed") is True, f"Expected allowed=True, got: {_pp(d)}")
    _assert(tool_list.get("ok") is True, f"Expected ok=True, got: {_pp(tool_list)}")

    # ------------------------------------------------------------
    # 4) OWNER checks (only if SSN_MASTER_KEY is set)
    # ------------------------------------------------------------
    if master_key:
        print("\n=== 4) OWNER Front Door checks ===")
        ctx_owner = {
            "session_id": "smoke",
            "turn_id": "3",
            "offline": bool(offline_forced),
            "allow_tools": True,
            "allow_research": True,
            "meta": {"master_key": master_key},
        }

        out3 = handle_user_message("knowledge: list what you know about SIONA", deps, ctx_owner)
        print(_pp(out3))
        _assert(isinstance(out3.get("answer"), str) and out3["answer"].strip(), "OWNER knowledge search did not return answer")

        out4 = handle_user_message("promote: This is a production smoke note.", deps, ctx_owner)
        print(_pp(out4))
        _assert("Knowledge promoted" in (out4.get("answer") or ""), "Expected knowledge promotion confirmation")

        print("\n=== 4a) OWNER InterfaceGateway run_tool tools.list ===")
        tool_all = _gateway_run_tool(runtime, role="OWNER", master_key=master_key, tool_name="tools.list", args={})
        print(_pp(tool_all))
        d_all = tool_all.get("data") if isinstance(tool_all.get("data"), dict) else {}
        _assert(d_all.get("identity_verified") is True, f"Expected identity_verified=True, got: {_pp(d_all)}")
        _assert(d_all.get("role") == "OWNER", f"Expected role=OWNER, got: {_pp(d_all)}")
        _assert(d_all.get("allowed") is True, f"Expected allowed=True, got: {_pp(d_all)}")
        _assert(tool_all.get("ok") is True, f"Expected ok=True, got: {_pp(tool_all)}")

        print("\n=== 4b) OWNER InterfaceGateway run_tool net.search ===")
        if offline_forced:
            print("[SKIP] SSN_OFFLINE=1 forces offline; net.search live calls are not expected to run.")
        else:
            tool_net = _gateway_run_tool(
                runtime,
                role="OWNER",
                master_key=master_key,
                tool_name="net.search",
                args={"query": "KSH to USD exchange rate today", "max_results": 3},
            )
            print(_pp(tool_net))
            _assert(tool_net.get("ok") is True, f"Expected OWNER net.search ok=True, got: {_pp(tool_net)}")

        print("\n=== 4c) OWNER InterfaceGateway world ===")
        req_world = InterfaceRequest(action="world", role="OWNER", user_input="", context={}, meta={"master_key": master_key})
        resp_world = runtime.gateway.handle(req_world)
        print(_pp({"ok": resp_world.ok, "data": resp_world.data, "error": (resp_world.error.__dict__ if resp_world.error else None)}))
        _assert(bool(resp_world.ok) is True, "Expected world ok=True")

        print("\n=== 4d) OWNER InterfaceGateway sense_tick ===")
        req_tick = InterfaceRequest(action="sense_tick", role="OWNER", user_input="", context={"max_events": 5}, meta={"master_key": master_key})
        resp_tick = runtime.gateway.handle(req_tick)
        print(_pp({"ok": resp_tick.ok, "data": resp_tick.data, "error": (resp_tick.error.__dict__ if resp_tick.error else None)}))
        _assert(bool(resp_tick.ok) is True, "Expected sense_tick ok=True")

    else:
        print("\n[INFO] SSN_MASTER_KEY not set; skipping OWNER-only smoke checks.")

    print("\n=== DONE: smoke_production.py PASSED ===")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as e:
        print("\n[FAIL]", str(e))
        raise SystemExit(2)
