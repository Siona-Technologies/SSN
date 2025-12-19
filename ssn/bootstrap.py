"""
SIONA Bootstrap

Purpose:
- Create a fully wired SIONA instance
- Register core tools
- Ensure ONE consistent initialization path

Every entry point (CLI, API, Voice, Robot) must call this.
"""

from __future__ import annotations
from typing import Optional, Any

from ssn.core.orchestrator import Orchestrator

# Tool imports
from ssn.tools.net_tools import NET_SEARCH_T
from ssn.tools.internet_research import INTERNET_RESEARCH_T


def create_siona(
    *,
    output_mode: str = "full",
    world_model: Optional[Any] = None,
) -> Orchestrator:
    """
    Create and return a fully initialized SIONA instance.

    This is the ONLY approved way to construct the system.
    """

    orch = Orchestrator(
        output_mode=output_mode,
        world_model=world_model,
    )

    # --------------------------------------------------
    # Tool registration (CORE)
    # --------------------------------------------------
    orch.tools.register(NET_SEARCH_T)
    orch.tools.register(INTERNET_RESEARCH_T)

    return orch
