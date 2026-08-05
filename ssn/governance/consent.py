"""Consent and co-founder authorization boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ssn.governance.information_classes import InformationClass
from ssn.governance.identity_records import IdentityFactRecord


# Canonical subject IDs for co-founders (non-sensitive).
SUBJECT_SAMSON = "person:samson-sibona-njaji"
SUBJECT_JAMES = "person:james-ndodana-njaji"
SUBJECT_OWNER_DEFAULT = SUBJECT_SAMSON


@dataclass(frozen=True)
class ConsentRecord:
    subject_id: str
    scope: str
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


def can_person_approve(
    *,
    actor_id: str,
    record: IdentityFactRecord,
    consent: Optional[ConsentRecord] = None,
) -> bool:
    """
    Approval authority:

    - OWNER_PRIVATE: verified owner / subject only
    - COFOUNDER_PRIVATE: only the subject (or explicit delegated consent);
      one co-founder cannot approve the other's private data by default
    - PUBLIC_* / COMPANY_CONFIDENTIAL / LEGAL_RESTRICTED: subject or designated
      company approver; still not auto-approved
    - SECRET / FORGET_DELETE: never approved into conversational memory
    """
    actor = (actor_id or "").strip()
    if not actor:
        return False

    cls = record.classification
    subject = (record.subject_id or "").strip()

    if cls in {InformationClass.SECRET, InformationClass.FORGET_DELETE}:
        return False

    if cls == InformationClass.COFOUNDER_PRIVATE:
        if consent is not None and consent_revoked(consent):
            return False
        if consent is not None and consent.granted and not consent.revoked:
            # Explicit delegation only when consent names the actor as grantor or scope.
            if consent.subject_id == subject and (
                consent.granted_by == actor or actor in (consent.scope or "")
            ):
                return actor == subject or "delegate:" + actor in (consent.scope or "")
        # Default: only the subject may approve their own private record.
        return bool(subject) and actor == subject

    if cls == InformationClass.OWNER_PRIVATE:
        return bool(subject) and actor == subject

    if cls in {
        InformationClass.PUBLIC_COMPANY,
        InformationClass.PUBLIC_PROFESSIONAL,
        InformationClass.COMPANY_CONFIDENTIAL,
        InformationClass.LEGAL_RESTRICTED,
    }:
        # Public/company facts still need a human approver; co-founder private
        # boundary does not apply, but actor must be non-empty and not "model".
        if actor.lower() in {"model", "llm", "siona", "self"}:
            return False
        return True

    # Missing / unknown classification: deny.
    return False


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
