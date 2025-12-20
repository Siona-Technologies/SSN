"""
SIONA Bootstrap

Purpose:
- Create a fully wired SIONA instance
- Register core tools
- Ensure ONE consistent initialization path

Every entry point (CLI, API, Voice, Robot) must call this.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ssn.core.orchestrator import Orchestrator

# Tool imports (production-direct net.* pipeline)
from ssn.tools.net_tools import NET_SEARCH_T
from ssn.tools.net_fetch import NET_FETCH_T
from ssn.tools.net_sanitize import NET_SANITIZE_T
from ssn.tools.net_cite import NET_CITE_T

from ssn.tools.research_ingest import RESEARCH_INGEST_T
from ssn.tools.research_answer import RESEARCH_ANSWER_T
from ssn.tools.research_propose import RESEARCH_PROPOSE_T

from ssn.tools.memory_propose import MEMORY_PROPOSE_T
from ssn.tools.memory_commit import MEMORY_COMMIT_T


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

    # Core tool registration (production-direct)
    for tool in (
        NET_SEARCH_T,
        NET_FETCH_T,
        NET_SANITIZE_T,
        NET_CITE_T,
        RESEARCH_INGEST_T,
        RESEARCH_ANSWER_T,
        RESEARCH_PROPOSE_T,
        MEMORY_PROPOSE_T,
        MEMORY_COMMIT_T,
    ):
        orch.tools.register(tool)

    return orch


def build_runtime(
    *,
    output_mode: str = "full",
    world_model: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Compatibility helper for scripts/tests that expect a dict runtime.

    Returns:
      {
        "orch": Orchestrator,
        "tools": ToolRegistry,
        "world_model": world_model,
      }
    """
    orch = create_siona(output_mode=output_mode, world_model=world_model)
    return {"orch": orch, "tools": orch.tools, "world_model": world_model}
