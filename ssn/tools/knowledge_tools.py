# ssn/tools/knowledge_tools.py

from __future__ import annotations

from ssn.tools.registry import ToolRegistry
from ssn.tools.knowledge_promote import KNOWLEDGE_PROMOTE_T
from ssn.tools.knowledge_search import KNOWLEDGE_SEARCH_T


def register_knowledge_tools(reg: ToolRegistry) -> None:
    reg.register(KNOWLEDGE_PROMOTE_T)
    reg.register(KNOWLEDGE_SEARCH_T)
