"""
Tool-call proposal validation (advisory only — never executes).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from ssn.cognition.model_gateway.contracts import ToolCallProposal

MAX_NAME = 128
MAX_CALL_ID = 128
MAX_REASON = 512
MAX_ARGS_KEYS = 32
MAX_ARGS_DEPTH = 4


@dataclass
class ProposalValidationResult:
    ok: bool
    reason: str = ""
    proposal: Optional[ToolCallProposal] = None


def _args_ok(args: Any, *, depth: int = 0) -> bool:
    if not isinstance(args, dict):
        return False
    if depth > MAX_ARGS_DEPTH:
        return False
    if len(args) > MAX_ARGS_KEYS:
        return False
    for v in args.values():
        if isinstance(v, dict) and not _args_ok(v, depth=depth + 1):
            return False
    return True


def validate_tool_proposal(proposal: ToolCallProposal) -> ProposalValidationResult:
    name = (proposal.name or "").strip()
    if not name:
        return ProposalValidationResult(False, "empty_name")
    if len(name) > MAX_NAME:
        return ProposalValidationResult(False, "name_too_long")
    if len(proposal.call_id or "") > MAX_CALL_ID:
        return ProposalValidationResult(False, "call_id_too_long")
    if len(proposal.reason or "") > MAX_REASON:
        return ProposalValidationResult(False, "reason_too_long")
    conf = float(proposal.confidence)
    if not math.isfinite(conf) or conf < 0.0 or conf > 1.0:
        return ProposalValidationResult(False, "invalid_confidence")
    if not _args_ok(proposal.arguments or {}):
        return ProposalValidationResult(False, "invalid_arguments")
    return ProposalValidationResult(True, "ok", proposal)


def validate_tool_proposals(proposals: List[ToolCallProposal]) -> ProposalValidationResult:
    if not proposals:
        return ProposalValidationResult(False, "empty_list")
    for p in proposals:
        result = validate_tool_proposal(p)
        if not result.ok:
            return result
    return ProposalValidationResult(True, "ok")
