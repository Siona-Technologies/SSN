# ssn/eval/scenarios.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ssn.interfaces.contracts import InterfaceRequest


@dataclass(frozen=True)
class Expectation:
    ok: Optional[bool] = None
    error_code: Optional[str] = None
    data_equals: Optional[Dict[str, Any]] = None
    data_has: Optional[List[str]] = None
    data_not_has: Optional[List[str]] = None


@dataclass(frozen=True)
class EvalScenario:
    name: str
    request: InterfaceRequest
    expect: Expectation


def default_eval_scenarios() -> list[EvalScenario]:
    """
    Deterministic baseline scenarios for the legacy ToolBus eval gateway.
    No secrets or network required.
    """
    return [
        EvalScenario(
            name="think_owner_requested_but_no_key_downgrades",
            request=InterfaceRequest(action="think", role="OWNER", user_input="hello", context={}, meta={}),
            expect=Expectation(ok=True, data_equals={"role": "GUEST"}),
        ),
        EvalScenario(
            name="toolbus_ping_available_for_guest",
            request=InterfaceRequest(action="tool", role="GUEST", meta={"tool_name": "toolbus.ping"}),
            expect=Expectation(ok=True, data_has=["pong"]),
        ),
        EvalScenario(
            name="toolbus_list_blocks_guest",
            request=InterfaceRequest(action="tool", role="GUEST", meta={"tool_name": "toolbus.list"}),
            expect=Expectation(ok=False, error_code="TOOL_OWNER_ONLY"),
        ),
        EvalScenario(
            name="toolbus_list_available_for_owner",
            request=InterfaceRequest(action="tool", role="OWNER", meta={"tool_name": "toolbus.list"}),
            expect=Expectation(ok=True, data_has=["tools"]),
        ),
        EvalScenario(
            name="safety_status_blocks_guest",
            request=InterfaceRequest(action="tool", role="GUEST", meta={"tool_name": "safety.status"}),
            expect=Expectation(ok=False, error_code="TOOL_OWNER_ONLY"),
        ),
        EvalScenario(
            name="unknown_tool_returns_not_found",
            request=InterfaceRequest(action="tool", role="OWNER", meta={"tool_name": "tools.list"}),
            expect=Expectation(ok=False, error_code="TOOL_NOT_FOUND"),
        ),
    ]


def production_eval_scenarios() -> list[EvalScenario]:
    """
    Scenarios that exercise the full runtime via SSNRuntimeBuilder + ToolRegistry.
    """
    return [
        EvalScenario(
            name="production_think_guest_hello",
            request=InterfaceRequest(
                action="think",
                role="GUEST",
                user_input="hello",
                context={},
                meta={},
            ),
            expect=Expectation(ok=True),
        ),
    ]
