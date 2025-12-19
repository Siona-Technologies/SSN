# ssn/tests/test_tool_approval_flow.py

from ssn.interfaces.contracts import InterfaceRequest
from ssn.interfaces.handlers_tools import handle_run_tool
from ssn.tools.registry import ToolRegistry
from ssn.tools.builtin_tools import register_builtin_tools

# ✅ IMPORTANT: mock owner verification cleanly
import ssn.identity.owner_verification as ov


class DummyMemoryHub:
    def __init__(self):
        self.traces = []

    def add_trace(self, payload):
        self.traces.append(payload)

    def get_recent_traces(self, limit=50):
        return self.traces[-limit:]


def make_deps():
    deps = {}
    deps["memory_hub"] = DummyMemoryHub()
    deps["tool_registry"] = ToolRegistry()
    register_builtin_tools(deps["tool_registry"])
    return deps


def fake_owner_request(tool_name, args=None):
    return InterfaceRequest(
        action="run_tool",
        role="OWNER",
        user_input="",
        context={
            "tool_name": tool_name,
            "args": args or {},
        },
        meta={
            # value does not matter because verification is mocked
            "master_key": "TEST_MASTER_KEY",
        },
    )


def fake_guest_request(tool_name, args=None):
    return InterfaceRequest(
        action="run_tool",
        role="GUEST",
        user_input="",
        context={
            "tool_name": tool_name,
            "args": args or {},
        },
        meta={},
    )


def run_tests():
    # --------------------------------------------------
    # MOCK OWNER VERIFICATION (CRITICAL)
    # --------------------------------------------------
    ov.verify_owner = lambda mk: {"score": 1.0}
    ov.is_samson_verified = lambda scores: True

    deps = make_deps()

    # --------------------------------------------------
    # 1. GUEST cannot access OWNER tools
    # --------------------------------------------------
    resp = handle_run_tool(fake_guest_request("tools.list"), deps)
    assert resp.data["final_result"] == "BLOCKED_BY_POLICY"

    # --------------------------------------------------
    # 2. OWNER can list tools
    # --------------------------------------------------
    resp = handle_run_tool(fake_owner_request("tools.list"), deps)
    assert resp.ok is True
    assert resp.data["result"] is not None
    assert "tools" in resp.data["result"]

    # --------------------------------------------------
    # 3. Read-only network tool works
    # --------------------------------------------------
    resp = handle_run_tool(
        fake_owner_request(
            "net.search",
            {"query": "SIONA architecture"},
        ),
        deps,
    )
    assert resp.ok is True
    assert resp.data["result"]["query"] == "SIONA architecture"

    # --------------------------------------------------
    # 4. State-changing but internal tool works (no approval)
    # --------------------------------------------------
    resp = handle_run_tool(
        fake_owner_request("world.sense_tick", {"max_events": 1}),
        deps,
    )
    assert resp.ok is True

    # --------------------------------------------------
    # 5. Media generation tool works (no approval)
    # --------------------------------------------------
    resp = handle_run_tool(
        fake_owner_request(
            "media.image.generate",
            {"prompt": "Test system diagram"},
        ),
        deps,
    )
    assert resp.ok is True
    assert "placeholder" in resp.data["result"]["note"].lower()

    # --------------------------------------------------
    # 6. Traces are written
    # --------------------------------------------------
    traces = deps["memory_hub"].get_recent_traces()
    assert len(traces) > 0

    found_tool_trace = any(t.get("type") == "tool_call" for t in traces)
    assert found_tool_trace is True

    print("\n✅ ALL TOOL APPROVAL FLOW TESTS PASSED\n")


if __name__ == "__main__":
    run_tests()
