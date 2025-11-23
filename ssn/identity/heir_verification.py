"""
SSN Identity Module: Heir Verification (Phase 1)

Purpose:
    Allow exactly one (or a few) pre-approved heirs to access SSN
    in strict emergency conditions when Samson is unavailable.

Design (Phase 1):
    - One configured heir id (e.g. "JAMES", "FAMILY-HEIR-1")
    - One emergency token (like a sealed phrase / code)
    - Optional behavior text check (weak signal)
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict

from .behavior_signature import generate_behavior_fingerprint


# -----------------------------------------------------------
# CONFIG (Phase 1 static config – later: move to secure vault)
# -----------------------------------------------------------

# You can change these later to real values.
# Think of them as the "heir username" and "heir secret token".
CONFIGURED_HEIR_ID = "HEIR-PRIMARY"
CONFIGURED_HEIR_TOKEN = "SIBONA-EMERGENCY-TOKEN-V1"

# Minimum overall score required to accept heir
MIN_HEIR_SCORE = 0.7


@dataclass
class HeirVerificationResult:
    is_heir: bool
    score: float
    reason: str


# -----------------------------------------------------------
# Internal helpers
# -----------------------------------------------------------

def _verify_heir_credentials(heir_id: str, token: str) -> float:
    """
    Very simple Phase-1 check:
    - 1.0 score if both id and token match exactly
    - 0.0 otherwise
    """
    if heir_id == CONFIGURED_HEIR_ID and token == CONFIGURED_HEIR_TOKEN:
        return 1.0
    return 0.0


def _score_behavior_similarity(behavior_text: Optional[str]) -> float:
    """
    Placeholder behavior similarity score for heir.

    For Phase 1:
    - If any behavior fingerprint fields are non-empty -> return 0.4
    - Else -> 0.0

    Rationale:
        Heir does not need to "match Samson", but we still want some
        form of stable input to avoid empty calls.
    """
    if not behavior_text:
        return 0.0

    fp: Dict[str, str] = generate_behavior_fingerprint(behavior_text)
    any_non_empty = any(bool(v) for v in fp.values())
    return 0.4 if any_non_empty else 0.0


# -----------------------------------------------------------
# Public API
# -----------------------------------------------------------

def verify_heir(
    heir_id: Optional[str],
    emergency_token: Optional[str],
    behavior_text: Optional[str] = None,
) -> HeirVerificationResult:
    """
    Main heir verification entry.

    Returns a struct with:
        - is_heir: bool
        - score: float (0.0 – 1.0)
        - reason: explanation string
    """
    if not heir_id or not emergency_token:
        return HeirVerificationResult(
            is_heir=False,
            score=0.0,
            reason="Missing heir id or emergency token",
        )

    cred_score = _verify_heir_credentials(heir_id, emergency_token)
    if cred_score == 0.0:
        return HeirVerificationResult(
            is_heir=False,
            score=0.0,
            reason="Heir credentials do not match configured heir",
        )

    behavior_score = _score_behavior_similarity(behavior_text)

    # Simple weighted average:
    #   credentials are strong (80%), behavior is weak (20%)
    overall = (cred_score * 0.8) + (behavior_score * 0.2)

    if overall >= MIN_HEIR_SCORE:
        return HeirVerificationResult(
            is_heir=True,
            score=overall,
            reason="Heir verified by credentials and behavior signal",
        )

    return HeirVerificationResult(
        is_heir=False,
        score=overall,
        reason="Heir credentials match but overall score below threshold",
    )
