# ssn/eval/runner.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from ssn.interfaces.contracts import InterfaceRequest, InterfaceResponse
from ssn.interfaces.gateway import InterfaceGateway
from ssn.interfaces.tool_bus import ToolBus
from ssn.interfaces.tools_builtin import register_builtin_tools

from ssn.eval.scenarios import EvalScenario, Expectation


# ----------------------------
# Deterministic test doubles
# ----------------------------

class PolicyAllowAll:
    def is_allowed(self, role, action, context=None, meta=None):
        return True


class SafetyAllow:
    def allow_internal_reflection(self):
        return True


class DummyMemoryHub:
    """
    Captures trace writes deterministically.
    """
    def __init__(self):
        self.traces = []

    def add_trace(self, payload=None, **kwargs):
        if payload is None:
            payload = kwargs.get("payload", {})
        self.traces.append(payload)

    def get_recent_traces(self, limit=50):
        return [{"payload": p} for p in self.traces[-limit:]]


class DummyOrchestratorIdentityAuthority:
    """
    Deterministic orchestrator that enforces identity authority:
    - OWNER only if master_key is a non-empty string (not role names)
    """

    def __init__(self):
        self.calls = 0
        self.last = {}

    def run(self, master_key=None, user_input=None, context=None, **kwargs):
        self.calls += 1
        mk: Optional[str] = None
        ui = user_input
        ctx = context if isinstance(context, dict) else {}

        # _call_compat may pass (role, user_input, context) positionally
        if master_key in ("OWNER", "GUEST") and isinstance(user_input, str):
            ui = user_input
            ctx = context if isinstance(context, dict) else {}
        elif isinstance(kwargs.get("role"), str) and kwargs["role"] in ("OWNER", "GUEST"):
            ui = kwargs.get("user_input", user_input)
            ctx = kwargs.get("context") if isinstance(kwargs.get("context"), dict) else ctx
        elif isinstance(master_key, str) and master_key.strip() and master_key not in ("OWNER", "GUEST"):
            mk = master_key.strip()
            ui = user_input
            ctx = context if isinstance(context, dict) else {}

        self.last = {"master_key": mk, "user_input": ui, "context": ctx}
        role = "OWNER" if mk else "GUEST"
        return {
            "identity_verified": role == "OWNER",
            "role": role,
            "allowed": True,
            "final_result": "EXECUTED",
        }


# ----------------------------
# Utilities
# ----------------------------

def _get_by_path(d: Any, path: str) -> Tuple[bool, Any]:
    """
    Dot-path getter for nested dicts.
    Returns (found, value).
    """
    if not isinstance(path, str) or not path:
        return False, None
    cur = d
    for part in path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return False, None
    return True, cur


def _assert_expectations(resp: InterfaceResponse, expect: Expectation) -> List[Dict[str, Any]]:
    """
    Returns a list of violations. Empty list => pass.
    """
    violations: List[Dict[str, Any]] = []

    if expect.ok is not None and bool(resp.ok) != bool(expect.ok):
        violations.append({"type": "ok_mismatch", "expected": expect.ok, "got": resp.ok})

    if expect.error_code is not None:
        got = resp.error.code if resp.error else None
        if got != expect.error_code:
            violations.append({"type": "error_code_mismatch", "expected": expect.error_code, "got": got})

    data = resp.data if isinstance(resp.data, dict) else {}

    if expect.data_equals:
        for p, v in expect.data_equals.items():
            found, got = _get_by_path(data, p)
            if not found:
                violations.append({"type": "data_missing", "path": p})
            elif got != v:
                violations.append({"type": "data_value_mismatch", "path": p, "expected": v, "got": got})

    if expect.data_has:
        for p in expect.data_has:
            found, _ = _get_by_path(data, p)
            if not found:
                violations.append({"type": "data_missing", "path": p})

    if expect.data_not_has:
        for p in expect.data_not_has:
            found, _ = _get_by_path(data, p)
            if found:
                violations.append({"type": "data_should_not_exist", "path": p})

    return violations


# ----------------------------
# Harness
# ----------------------------

@dataclass
class ScenarioResult:
    name: str
    passed: bool
    violations: List[Dict[str, Any]]
    response_snapshot: Dict[str, Any]


class EvalRunner:
    """
    Runs deterministic scenarios through an InterfaceGateway.
    """

    def __init__(self, gateway: InterfaceGateway):
        self.gateway = gateway

    def run_one(self, scenario: EvalScenario) -> ScenarioResult:
        resp = self.gateway.handle(scenario.request)
        violations = _assert_expectations(resp, scenario.expect)

        snap = {
            "ok": resp.ok,
            "action": resp.action,
            "role": resp.role,
            "data": resp.data,
            "error": None if resp.error is None else {
                "code": resp.error.code,
                "message": resp.error.message,
                "details": resp.error.details,
            }
        }

        return ScenarioResult(
            name=scenario.name,
            passed=(len(violations) == 0),
            violations=violations,
            response_snapshot=snap,
        )

    def run_all(self, scenarios: List[EvalScenario]) -> Dict[str, Any]:
        results: List[ScenarioResult] = [self.run_one(s) for s in scenarios]
        passed = sum(1 for r in results if r.passed)
        failed = len(results) - passed

        return {
            "summary": {
                "total": len(results),
                "passed": passed,
                "failed": failed,
            },
            "results": [
                {
                    "name": r.name,
                    "passed": r.passed,
                    "violations": r.violations,
                    "response_snapshot": r.response_snapshot,
                }
                for r in results
            ],
        }


def build_default_eval_gateway() -> Dict[str, Any]:
    """
    Builds a deterministic evaluation gateway with:
    - Dummy orchestrator (identity authority)
    - Dummy memory hub (trace capture)
    - ToolBus with built-ins
    - Policy + safety allow
    """
    bus = ToolBus()
    register_builtin_tools(bus)

    mh = DummyMemoryHub()
    orch = DummyOrchestratorIdentityAuthority()

    gw = InterfaceGateway(
        orchestrator=orch,
        policy_engine=PolicyAllowAll(),
        safety_monitor=SafetyAllow(),
        tool_bus=bus,
        memory_hub=mh,
    )

    return {
        "gateway": gw,
        "tool_bus": bus,
        "memory_hub": mh,
        "orchestrator": orch,
    }


def build_production_eval_gateway() -> Dict[str, Any]:
    """
    Full runtime gateway via SSNRuntimeBuilder (create_siona bootstrap path).
    """
    from ssn.runtime.runtime_builder import SSNRuntimeBuilder

    rt = SSNRuntimeBuilder.build_default(default_role="GUEST")
    return {
        "gateway": rt.gateway,
        "runtime": rt,
        "orchestrator": rt.orchestrator,
        "tool_registry": rt.tool_registry,
    }
