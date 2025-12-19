# ssn/tests/test_internet_research_basic.py

from ssn.tools.registry import ToolRegistry
from ssn.tools.internet_research import INTERNET_RESEARCH_TOOL


def test_internet_research_owner_allowed():
    registry = ToolRegistry()
    registry.register(INTERNET_RESEARCH_TOOL)

    result = registry.run(
        name="internet_research",
        role="OWNER",
        deps={},
        args={"query": "What is spiking neural networks?"},
    )

    assert result.ok is True
    assert "results" in result.data
    assert isinstance(result.data["results"], list)


def test_internet_research_guest_blocked():
    registry = ToolRegistry()
    registry.register(INTERNET_RESEARCH_TOOL)

    result = registry.run(
        name="internet_research",
        role="GUEST",
        deps={},
        args={"query": "test"},
    )

    assert result.ok is False
    assert result.error["code"] == "TOOL_FORBIDDEN"
