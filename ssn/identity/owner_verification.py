"""
Owner Verification System (Phase 1)

This module verifies whether the current user is Samson.

It integrates (for now):
- Master Key Identity  (strong, required)
- Biometric Signature  (placeholder)
- Behavior Signature   (placeholder)

Phase 1:
    Master key is the only strict requirement.
    Biometric + behavior just act as extra weak signals.
"""

from __future__ import annotations
from typing import Optional, Dict

from .master_key import verify_master_key as _verify_master_key
from .biometric_signature import generate_biometric_fingerprint
from .behavior_signature import generate_behavior_fingerprint


# -----------------------------------------------------------
# Thresholds (Phase 1)
# -----------------------------------------------------------
THRESHOLDS = {
    "master_key": 1.0,   # must be exact
    "biometric": 0.0,    # not enforced yet
    "behavior": 0.0,     # not enforced yet
}


def _score_biometric(sample: Dict[str, str]) -> float:
    """
    Very simple placeholder scoring:
    - If any biometric field is non-empty -> 0.5
    - Else -> 0.0

    In future phases this will become a real similarity score.
    """
    if not sample:
        return 0.0

    any_non_empty = any(bool(v) for v in sample.values())
    return 0.5 if any_non_empty else 0.0


def _score_behavior(fingerprint: Dict[str, str]) -> float:
    """
    Placeholder scoring for behavior:
    - If any behavioral feature is non-empty -> 0.5
    - Else -> 0.0
    """
    if not fingerprint:
        return 0.0

    any_non_empty = any(bool(v) for v in fingerprint.values())
    return 0.5 if any_non_empty else 0.0


def verify_owner(
    master_key: Optional[str],
    face_bytes: Optional[bytes] = None,
    voice_bytes: Optional[bytes] = None,
    gait_data: Optional[str] = None,
    typing_pattern: Optional[str] = None,
    behavior_text: Optional[str] = None,
) -> Dict[str, float]:
    """
    Main verification entry point.

    Returns a dict of scores:
    {
        "master_key_score": float,
        "biometric_score":  float,
        "behavior_score":   float,
        "overall_score":    float,
    }
    """

    # 1. Master Key
    master_ok = _verify_master_key(master_key)
    master_score = 1.0 if master_ok else 0.0

    # 2. Biometric fingerprints (placeholder)
    biometric_fp = generate_biometric_fingerprint(
        face=face_bytes,
        voice=voice_bytes,
        gait=gait_data,
        typing=typing_pattern,
    )
    biometric_score = _score_biometric(biometric_fp)

    # 3. Behavior fingerprint (placeholder)
    behavior_fp = generate_behavior_fingerprint(behavior_text)
    behavior_score = _score_behavior(behavior_fp)

    # 4. Overall score (simple weighted average for now)
    overall = (master_score * 0.7) + (biometric_score * 0.15) + (behavior_score * 0.15)

    return {
        "master_key_score": master_score,
        "biometric_score": biometric_score,
        "behavior_score": behavior_score,
        "overall_score": overall,
    }


def is_samson_verified(scores: Dict[str, float]) -> bool:
    """
    Final gatekeeper.

    For Phase 1:
    - master_key_score MUST meet its threshold
    - biometric + behavior thresholds are 0.0 (not enforced yet)
    """
    return (
        scores["master_key_score"] >= THRESHOLDS["master_key"]
        and scores["biometric_score"] >= THRESHOLDS["biometric"]
        and scores["behavior_score"] >= THRESHOLDS["behavior"]
    )
