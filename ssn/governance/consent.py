"""Consent and co-founder authorization boundaries (exact matching only)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from ssn.governance.information_classes import AllowedUse, InformationClass
from ssn.governance.identity_records import IdentityFactRecord


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
    return bool(consent.revoked) or not bool(consent.granted)


def validate_consent(consent: ConsentRecord) -> Tuple[bool, str]:
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
    if consent.revoked and not (consent.revoked_at or "").strip():
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


def can_person_approve(
    *,
    actor_id: str,
    actor_authenticated: bool,
    record: IdentityFactRecord,
    authorized_company_approver_ids: Tuple[str, ...] = (),
    consent: Optional[ConsentRecord] = None,
) -> bool:
    """
    Approval authority (authenticated actors only).

    - Subject may approve their own record without prior delegation.
    - Delegated approval requires a valid ConsentRecord with exact grantee
      and AllowedUse that includes an approval-capable use when supplied;
      for approval actions we accept OWNER_ASSISTANCE or a dedicated match
      only when consent.allowed_uses is non-empty and actor is exact grantee.
    - Company/public/legal: subject or exact authorized company approver.
    - SECRET / FORGET_DELETE: never.
    """
    if not actor_authenticated:
        return False
    actor = (actor_id or "").strip()
    if not actor or is_model_identity(actor):
        return False

    cls = record.classification
    subject = (record.subject_id or "").strip()

    if cls is None or cls in {InformationClass.SECRET, InformationClass.FORGET_DELETE}:
        return False

    # Subject self-approval of their own record.
    if subject and actor == subject:
        return True

    # Exact delegated approval (subject-issued).
    if consent is not None:
        # Approval delegation: require valid consent naming this actor as grantee.
        # Requested use for approval is treated as OWNER_ASSISTANCE membership in
        # allowed_uses (structured enum list — exact membership, not substring).
        ok, _reason = delegation_allows(
            consent, actor_id=actor, requested_use=AllowedUse.OWNER_ASSISTANCE
        )
        if ok and consent.subject_id == subject:
            return True

    if cls in {
        InformationClass.PUBLIC_COMPANY,
        InformationClass.PUBLIC_PROFESSIONAL,
        InformationClass.COMPANY_CONFIDENTIAL,
        InformationClass.LEGAL_RESTRICTED,
    }:
        if actor in set(authorized_company_approver_ids or ()):
            return True
        return False

    if cls in {InformationClass.OWNER_PRIVATE, InformationClass.COFOUNDER_PRIVATE}:
        # Non-subject without valid delegation: deny.
        return False

    return False
