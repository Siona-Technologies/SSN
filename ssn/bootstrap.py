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

# ---------------------------------------------------------
# Tool imports (production-direct net.* + research.* + memory.*)
# ---------------------------------------------------------

# Phase 7.2 — Network research tools
from ssn.tools.net_tools import NET_SEARCH_T
from ssn.tools.net_fetch import NET_FETCH_T
from ssn.tools.net_sanitize import NET_SANITIZE_T
from ssn.tools.net_cite import NET_CITE_T

# Phase 7.3 — Research tools
from ssn.tools.research_ingest import RESEARCH_INGEST_T
from ssn.tools.research_answer import RESEARCH_ANSWER_T
from ssn.tools.research_propose import RESEARCH_PROPOSE_T

# Memory proposal/commit (explicit write path)
from ssn.tools.memory_propose import MEMORY_PROPOSE_T
from ssn.tools.memory_commit import MEMORY_COMMIT_T

# Pending proposal inspection tools (disk-canonical, read-only)
from ssn.tools.memory_pending_tools import MEMORY_PENDING_LIST_T, MEMORY_PENDING_GET_T

# Phase 7.4 — Local knowledge promotion/search
from ssn.tools.knowledge_promote import KNOWLEDGE_PROMOTE_T
from ssn.tools.knowledge_search import KNOWLEDGE_SEARCH_T

# Built-in tools (tools.list, tools.public_list, world.*, memory.summary, etc.)
from ssn.tools.builtin_tools import register_builtin_tools


def _maybe_load_dotenv() -> None:
    """
    Optional: load .env automatically for local/dev convenience.
    Controlled by env flag to avoid surprising CI/prod.

    Enable by setting:
      SSN_AUTO_DOTENV=1
    """
    import os

    if os.getenv("SSN_AUTO_DOTENV") != "1":
        return

    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:
        # If python-dotenv isn't installed, fail silently (dev convenience only).
        return

    load_dotenv()


def _tool_exists(orch: Orchestrator, name: str) -> bool:
    """
    ToolRegistry.list() shape can vary (dict or list). Handle both.
    """
    try:
        listing = orch.tools.list()
        if isinstance(listing, dict):
            return name in listing
        if isinstance(listing, list):
            return name in listing
    except Exception:
        return False
    return False


def _register_once(orch: Orchestrator, tool: Any) -> None:
    """
    Register tool if not already present.
    Keeps bootstrap idempotent across entry points/tests.
    """
    name = getattr(tool, "name", None)
    if isinstance(name, str) and name and _tool_exists(orch, name):
        return
    orch.tools.register(tool)


def create_siona(
    *,
    output_mode: str = "full",
    world_model: Optional[Any] = None,
) -> Orchestrator:
    """
    Create and return a fully initialized SIONA instance.

    This is the ONLY approved way to construct the system.
    """
    _maybe_load_dotenv()

    orch = Orchestrator(
        output_mode=output_mode,
        world_model=world_model,
    )

    # ---------------------------------------------------------
    # Register builtin tools first (ensures tools.list exists)
    # ---------------------------------------------------------
    if not _tool_exists(orch, "tools.list"):
        register_builtin_tools(orch.tools)

    # ---------------------------------------------------------
    # Register production-direct tools (net.*, research.*, memory commit path, knowledge.*)
    # ---------------------------------------------------------
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
        MEMORY_PENDING_LIST_T,
        MEMORY_PENDING_GET_T,
        KNOWLEDGE_PROMOTE_T,
        KNOWLEDGE_SEARCH_T,
    ):
        _register_once(orch, tool)

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
