"""Consent and co-founder authorization boundaries (exact matching only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from ssn.governance.information_classes import AllowedUse
from ssn.governance.identity_records import is_valid_iso_instant


# Canonical subject IDs for co-founders (non-sensitive).
SUBJECT_SAMSON = "person:samson-sibona-njaji"
SUBJECT_JAMES = "person:james-ndodana-njaji"
SUBJECT_OWNER_DEFAULT = SUBJECT_SAMSON

_MODEL_IDENTITIES = frozenset({"model", "llm", "siona", "self", "system"})


@dataclass(frozen=True)
class ConsentRecord:
    """Structured subject-issued delegation. No free-form scope matching."""

    subject_id: str
    grantee_id: str
    allowed_uses: Tuple[AllowedUse, ...]
    granted: bool
    granted_by: str
    timestamp: str
    revoked: bool = False
    revoked_at: str = ""
    notes: str = ""


def consent_revoked(consent: Optional[ConsentRecord]) -> bool:
    if consent is None:
        return False
    # Fail closed on non-bool fields (must not use general truthiness).
    if type(consent.revoked) is not bool or type(consent.granted) is not bool:
        return True
    return consent.revoked or not consent.granted


def validate_consent(consent: ConsentRecord) -> Tuple[bool, str]:
    if type(consent.granted) is not bool or type(consent.revoked) is not bool:
        return False, "invalid_consent_boolean"

    subject = (consent.subject_id or "").strip()
    grantee = (consent.grantee_id or "").strip()
    granted_by = (consent.granted_by or "").strip()
    if not subject:
        return False, "invalid_consent_subject"
    if not grantee:
        return False, "invalid_consent_grantee"
    if not granted_by:
        return False, "invalid_consent_grantor"
    # Subject-issued delegation only.
    if granted_by != subject:
        return False, "deny_consent_not_subject_issued"
    if not isinstance(consent.allowed_uses, tuple) or not consent.allowed_uses:
        return False, "invalid_consent_allowed_uses"
    for use in consent.allowed_uses:
        if not isinstance(use, AllowedUse):
            return False, "invalid_consent_allowed_uses"

    ok_ts, _ = is_valid_iso_instant(consent.timestamp)
    if not ok_ts:
        return False, "invalid_consent_timestamp"

    revoked_at = (consent.revoked_at or "").strip()
    if consent.revoked:
        ok_rev, _ = is_valid_iso_instant(revoked_at)
        if not ok_rev:
            return False, "invalid_consent_revoked_at"
    elif revoked_at:
        # Active consents must not carry a revocation timestamp.
        return False, "invalid_consent_revoked_at"

    if len(subject) > 256 or len(grantee) > 256 or len(granted_by) > 256:
        return False, "invalid_consent_field_length"
    return True, "ok"


def delegation_allows(
    consent: Optional[ConsentRecord],
    *,
    actor_id: str,
    requested_use: AllowedUse,
) -> Tuple[bool, str]:
    """Exact delegated access check. Missing consent denies delegated use."""
    if consent is None:
        return False, "deny_missing_consent"
    ok, reason = validate_consent(consent)
    if not ok:
        return False, reason
    if consent_revoked(consent):
        return False, "deny_consent_revoked"
    # granted=False never authorizes (also covered by consent_revoked).
    if consent.granted is not True:
        return False, "deny_consent_revoked"
    actor = (actor_id or "").strip()
    if not actor or actor != consent.grantee_id:
        return False, "deny_delegate_mismatch"
    if requested_use not in consent.allowed_uses:
        return False, "deny_use_not_in_consent"
    return True, "allow_delegate"


def is_model_identity(actor_id: str) -> bool:
    return (actor_id or "").strip().lower() in _MODEL_IDENTITIES


def other_cofounder_cannot_approve_private(
    *,
    actor_id: str,
    subject_id: str,
) -> bool:
    """True when actor is attempting to approve the other co-founder's private data."""
    actor = (actor_id or "").strip()
    subject = (subject_id or "").strip()
    cofounders = {SUBJECT_SAMSON, SUBJECT_JAMES}
    if actor not in cofounders or subject not in cofounders:
        return False
    return actor != subject
