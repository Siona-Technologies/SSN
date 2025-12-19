# ssn/tests/test_orchestrator_internet_research.py

from ssn.core.orchestrator import Orchestrator
from ssn.tools.internet_research import INTERNET_RESEARCH_T


def test_orchestrator_internet_research_owner():
    """
    OWNER should be able to execute the internet research tool
    through the orchestrator pipeline.
    """

    orch = Orchestrator(output_mode="full")

    # Register the tool explicitly
    orch.tools.register(INTERNET_RESEARCH_T)

    # Simulate OWNER request that triggers tool usage
    # NOTE: we inject tool_call directly into context to avoid
    # coupling this test to LLM behavior.
    response = orch.run(
        master_key="VALID_OWNER_KEY",
        user_input="Research spiking neural networks",
        context={
            "force_tool_call": {
                "name": "internet_research",
                "args": {"query": "Spiking Neural Networks overview"},
            }
        },
    )

    # Basic sanity
    assert response["allowed"] is True
    assert response["role"] == "OWNER"

    # Tool result must exist
    tool_result = response.get("tool_result")
    assert tool_result is not None
    assert tool_result["ok"] is True
    assert tool_result["tool"] == "internet_research"

    data = tool_result["data"]
    assert "results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) > 0


def test_orchestrator_internet_research_guest_blocked():
    """
    GUEST should NOT be allowed to execute the internet research tool.
    """

    orch = Orchestrator(output_mode="full")
    orch.tools.register(INTERNET_RESEARCH_T)

    response = orch.run(
        master_key=None,  # not OWNER
        user_input="Research spiking neural networks",
        context={
            "force_tool_call": {
                "name": "internet_research",
                "args": {"query": "Spiking Neural Networks overview"},
            }
        },
    )

    assert response["allowed"] is True
    assert response["role"] == "GUEST"

    tool_result = response.get("tool_result")

    # Tool execution should fail or be absent
    if tool_result is not None:
        assert tool_result["ok"] is False
