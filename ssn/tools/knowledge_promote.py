from __future__ import annotations

from typing import Any, Dict, List, Optional

from ssn.tools.contracts import ToolSpec
from ssn.knowledge.store import KnowledgeStore


def _safe_list_dict(x: Any, cap: int) -> List[Dict[str, Any]]:
    if not isinstance(x, list):
        return []
    out: List[Dict[str, Any]] = []
    for it in x:
        if isinstance(it, dict):
            out.append(it)
        if len(out) >= cap:
            break
    return out


def knowledge_promote_handler(deps: Dict[str, Any], args: Dict[str, Any]) -> Dict[str, Any]:
    role = deps.get("role") or "OWNER"
    if role != "OWNER":
        return {"error": {"code": "FORBIDDEN", "message": "knowledge.promote is OWNER-only"}}

    # You can promote either:
    # (A) explicit title/text, or (B) a research.answer output dict via "research_output"
    title = args.get("title")
    text = args.get("text")
    tags = args.get("tags")

    research_output = args.get("research_output")
    if isinstance(research_output, dict):
        # Promote the *answer* only (curated), with sources/citations attached
        title = title if isinstance(title, str) and title.strip() else f"Research: {research_output.get('query', '')}".strip()[:240]
        text = text if isinstance(text, str) and text.strip() else (research_output.get("answer") or "")
        sources = _safe_list_dict(research_output.get("sources"), 50)
        citations = _safe_list_dict(research_output.get("citations"), 80)
        provenance = {
            "query": research_output.get("query"),
            "answered_at": research_output.get("answered_at"),
            "degraded": research_output.get("degraded"),
            "search": research_output.get("search"),
        }
    else:
        sources = _safe_list_dict(args.get("sources"), 50)
        citations = _safe_list_dict(args.get("citations"), 80)
        provenance = args.get("provenance") if isinstance(args.get("provenance"), dict) else {}

    if not isinstance(title, str):
        title = ""
    if not isinstance(text, str):
        text = ""

    tags_list: Optional[List[str]] = None
    if isinstance(tags, list):
        tags_list = [t for t in tags if isinstance(t, str)]

    ks = KnowledgeStore()
    pr = ks.promote(
        title=title,
        text=text,
        tags=tags_list or [],
        sources=sources,
        citations=citations,
        provenance=provenance,
    )

    if not pr.get("ok", False):
        return {"error": pr.get("error") or {"code": "PROMOTE_FAILED", "message": "Promotion failed"}}

    return {
        "kid": pr["kid"],
        "status": pr["status"],
        "note": "knowledge.promote (Phase 7.4, explicit owner enrollment; writes local knowledge store)",
    }


KNOWLEDGE_PROMOTE_T = ToolSpec(
    name="knowledge.promote",
    description="Promote curated text into local knowledge store (OWNER-only, explicit write).",
    required_role="OWNER",
    allowed_roles=("OWNER",),
    state_changing=True,
    external_effect=False,
    public=False,
    max_calls_per_minute=30,
    input_schema={
        "title": {"type": "string", "required": False, "description": "Knowledge title"},
        "text": {"type": "string", "required": False, "description": "Knowledge text to store"},
        "tags": {"type": "array", "required": False, "description": "Optional tags"},
        "sources": {"type": "array", "required": False, "description": "Optional sources list"},
        "citations": {"type": "array", "required": False, "description": "Optional citations list"},
        "provenance": {"type": "object", "required": False, "description": "Optional provenance dict"},
        "research_output": {"type": "object", "required": False, "description": "Optional research.answer output to promote"},
    },
    handler=knowledge_promote_handler,
)
