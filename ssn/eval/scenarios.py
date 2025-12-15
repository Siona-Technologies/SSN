# ssn/eval/scenarios.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, List

from ssn.interfaces.contracts import InterfaceRequest


@dataclass(frozen=True)
class Expectation:
    ok: Optional[bool] = None
    error_code: Optional[str] = None
    # Assertions on response.data (dot-path -> expected value)
    data_equals: Optional[Dict[str, Any]] = None
    # Assertions on presence of keys in response.data (dot-path)
    data_has: Optional[List[str]] = None
    # Assertions on keys NOT present in response.data
    data_not_has: Optional[List[str]] = None


@dataclass(frozen=True)
class EvalScenario:
    name: str
    request: InterfaceRequest
    expect: Expectation


def default_eval_scenarios() -> list[EvalScenario]:
    """
    Deterministic baseline scenarios. These do not require any secrets or external resources.
    """
    return [
        EvalScenario(
            name="think_owner_requested_but_no_key_downgrades",
            request=InterfaceRequest(action="think", role="OWNER", user_input="hello", context={}, meta={}),
            expect=Expectation(ok=True, data_equals={"role": "GUEST"}),
        ),
        EvalScenario(
            name="tools_list_available_for_guest",
            request=InterfaceRequest(action="tool", role="GUEST", meta={"tool_name": "tools.list"}),
            expect=Expectation(ok=True, data_has=["tools"]),
        ),
        EvalScenario(
            name="memory_types_owner_only_blocks_guest",
            request=InterfaceRequest(action="tool", role="GUEST", meta={"tool_name": "memory.types", "trace_limit": 10}),
            expect=Expectation(ok=False, error_code="TOOL_OWNER_ONLY"),
        ),
        EvalScenario(
            name="doc_ingest_owner_writes_bounded_trace",
            request=InterfaceRequest(
                action="tool",
                role="OWNER",
                meta={
                    "tool_name": "doc.ingest_readonly",
                    "format": "text",
                    "title": "Eval Doc",
                    "document": "Line1\nLine2 must remain bounded\nLine3",
                    "max_citations": 5,
                },
            ),
            expect=Expectation(
                ok=True,
                data_equals={"trace_written": True},
                data_has=["content_hash", "citations", "summary_bullets"],
            ),
        ),
    ]
