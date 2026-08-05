"""Deterministic information-use policy decisions (deny by default)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from ssn.governance.consent import ConsentRecord, can_person_approve, consent_revoked
from ssn.governance.identity_records import (
    IdentityFactRecord,
    model_output_cannot_self_approve,
)
from ssn.governance.information_classes import (
    AllowedUse,
    ApprovalStatus,
    InformationClass,
)


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    use: str = ""


def _parse_date(value: str) -> Optional[date]:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _is_expired(record: IdentityFactRecord, *, today: Optional[date] = None) -> bool:
    if record.approval_status == ApprovalStatus.EXPIRED:
        return True
    review = _parse_date(record.review_date)
    if review is None:
        return False
    now = today or date.today()
    return now > review


def _base_denial(record: IdentityFactRecord) -> Optional[PolicyDecision]:
    if record.classification is None:
        return PolicyDecision(False, "deny_missing_classification")
    if record.classification == InformationClass.SECRET:
        return PolicyDecision(False, "deny_secret")
    if record.classification == InformationClass.FORGET_DELETE:
        return PolicyDecision(False, "deny_forget_delete")
    if (record.revocation_status or "").strip().lower() == "revoked":
        return PolicyDecision(False, "deny_revoked")
    if record.approval_status == ApprovalStatus.REVOKED:
        return PolicyDecision(False, "deny_revoked")
    if record.approval_status == ApprovalStatus.REJECTED:
        return PolicyDecision(False, "deny_rejected")
    if _is_expired(record):
        return PolicyDecision(False, "deny_expired")
    if model_output_cannot_self_approve(record):
        return PolicyDecision(False, "deny_model_cannot_self_approve")
    return None


def _use_prohibited(record: IdentityFactRecord, use: AllowedUse) -> bool:
    return use in set(record.prohibited_uses or ())


def decide_public(
    record: IdentityFactRecord,
    *,
    today: Optional[date] = None,
) -> PolicyDecision:
    denied = _base_denial(record)
    if denied:
        return PolicyDecision(denied.allowed, denied.reason, AllowedUse.PUBLIC_RESPONSE.value)
    if record.classification not in {
        InformationClass.PUBLIC_COMPANY,
        InformationClass.PUBLIC_PROFESSIONAL,
    }:
        return PolicyDecision(False, "deny_not_public_class", AllowedUse.PUBLIC_RESPONSE.value)
    if record.approval_status != ApprovalStatus.APPROVED:
        return PolicyDecision(False, "deny_not_approved", AllowedUse.PUBLIC_RESPONSE.value)
    if _is_expired(record, today=today):
        return PolicyDecision(False, "deny_expired", AllowedUse.PUBLIC_RESPONSE.value)
    if _use_prohibited(record, AllowedUse.PUBLIC_RESPONSE):
        return PolicyDecision(False, "deny_prohibited_use", AllowedUse.PUBLIC_RESPONSE.value)
    return PolicyDecision(True, "allow_public_approved", AllowedUse.PUBLIC_RESPONSE.value)


def decide_owner_assistance(
    record: IdentityFactRecord,
    *,
    requester_id: str,
    verified_owner: bool,
    consent: Optional[ConsentRecord] = None,
) -> PolicyDecision:
    denied = _base_denial(record)
    if denied:
        return PolicyDecision(denied.allowed, denied.reason, AllowedUse.OWNER_ASSISTANCE.value)

    cls = record.classification
    assert cls is not None

    if cls == InformationClass.LEGAL_RESTRICTED:
        return PolicyDecision(False, "deny_legal_not_ordinary_memory", AllowedUse.OWNER_ASSISTANCE.value)

    if cls == InformationClass.OWNER_PRIVATE:
        if not verified_owner:
            return PolicyDecision(False, "deny_guest_owner_private", AllowedUse.OWNER_ASSISTANCE.value)
        if requester_id != (record.subject_id or ""):
            return PolicyDecision(False, "deny_wrong_owner_subject", AllowedUse.OWNER_ASSISTANCE.value)
        return PolicyDecision(True, "allow_owner_private", AllowedUse.OWNER_ASSISTANCE.value)

    if cls == InformationClass.COFOUNDER_PRIVATE:
        if consent_revoked(consent):
            return PolicyDecision(False, "deny_consent_revoked", AllowedUse.OWNER_ASSISTANCE.value)
        if requester_id != (record.subject_id or ""):
            return PolicyDecision(
                False, "deny_other_cofounder_private", AllowedUse.OWNER_ASSISTANCE.value
            )
        return PolicyDecision(True, "allow_cofounder_subject", AllowedUse.OWNER_ASSISTANCE.value)

    if cls == InformationClass.COMPANY_CONFIDENTIAL:
        if not verified_owner:
            return PolicyDecision(False, "deny_guest_confidential", AllowedUse.OWNER_ASSISTANCE.value)
        return PolicyDecision(True, "allow_owner_confidential", AllowedUse.OWNER_ASSISTANCE.value)

    if cls in {InformationClass.PUBLIC_COMPANY, InformationClass.PUBLIC_PROFESSIONAL}:
        pub = decide_public(record)
        if pub.allowed:
            return PolicyDecision(True, "allow_public_for_owner", AllowedUse.OWNER_ASSISTANCE.value)
        # Draft public facts may still assist the subject/owner privately only when DRAFT.
        if verified_owner and record.approval_status == ApprovalStatus.DRAFT:
            return PolicyDecision(True, "allow_draft_owner_review", AllowedUse.OWNER_ASSISTANCE.value)
        return PolicyDecision(False, pub.reason, AllowedUse.OWNER_ASSISTANCE.value)

    return PolicyDecision(False, "deny_by_default", AllowedUse.OWNER_ASSISTANCE.value)


def decide_model_prompt(record: IdentityFactRecord) -> PolicyDecision:
    denied = _base_denial(record)
    if denied:
        return PolicyDecision(denied.allowed, denied.reason, AllowedUse.MODEL_PROMPT.value)
    if record.classification == InformationClass.LEGAL_RESTRICTED:
        return PolicyDecision(False, "deny_legal_not_prompt", AllowedUse.MODEL_PROMPT.value)
    if record.classification == InformationClass.SECRET:
        return PolicyDecision(False, "deny_secret", AllowedUse.MODEL_PROMPT.value)
    if _use_prohibited(record, AllowedUse.MODEL_PROMPT):
        return PolicyDecision(False, "deny_prohibited_use", AllowedUse.MODEL_PROMPT.value)
    if record.classification in {
        InformationClass.PUBLIC_COMPANY,
        InformationClass.PUBLIC_PROFESSIONAL,
    }:
        if record.approval_status != ApprovalStatus.APPROVED:
            return PolicyDecision(False, "deny_not_approved_for_prompt", AllowedUse.MODEL_PROMPT.value)
        return PolicyDecision(True, "allow_approved_public_prompt", AllowedUse.MODEL_PROMPT.value)
    if record.classification in {
        InformationClass.OWNER_PRIVATE,
        InformationClass.COFOUNDER_PRIVATE,
        InformationClass.COMPANY_CONFIDENTIAL,
    }:
        # Prompt insertion still requires a separate authorized assistance path;
        # this gate alone does not publish. Conservative default: deny unless
        # explicitly intended.
        if AllowedUse.MODEL_PROMPT in set(record.intended_uses or ()):
            return PolicyDecision(True, "allow_intended_private_prompt", AllowedUse.MODEL_PROMPT.value)
        return PolicyDecision(False, "deny_private_prompt_not_intended", AllowedUse.MODEL_PROMPT.value)
    return PolicyDecision(False, "deny_by_default", AllowedUse.MODEL_PROMPT.value)


def decide_embed(record: IdentityFactRecord) -> PolicyDecision:
    denied = _base_denial(record)
    if denied:
        return PolicyDecision(denied.allowed, denied.reason, AllowedUse.RETRIEVAL.value)
    if record.classification in {
        InformationClass.SECRET,
        InformationClass.FORGET_DELETE,
        InformationClass.LEGAL_RESTRICTED,
    }:
        return PolicyDecision(False, "deny_restricted_embed", AllowedUse.RETRIEVAL.value)
    if _use_prohibited(record, AllowedUse.RETRIEVAL):
        return PolicyDecision(False, "deny_prohibited_use", AllowedUse.RETRIEVAL.value)
    if record.classification in {
        InformationClass.PUBLIC_COMPANY,
        InformationClass.PUBLIC_PROFESSIONAL,
    } and record.approval_status == ApprovalStatus.APPROVED:
        return PolicyDecision(True, "allow_approved_public_embed", AllowedUse.RETRIEVAL.value)
    return PolicyDecision(False, "deny_embed_by_default", AllowedUse.RETRIEVAL.value)


def decide_log(record: IdentityFactRecord) -> PolicyDecision:
    denied = _base_denial(record)
    if denied:
        return PolicyDecision(denied.allowed, denied.reason, "LOG")
    if record.classification in {
        InformationClass.SECRET,
        InformationClass.FORGET_DELETE,
        InformationClass.LEGAL_RESTRICTED,
        InformationClass.OWNER_PRIVATE,
        InformationClass.COFOUNDER_PRIVATE,
    }:
        return PolicyDecision(False, "deny_sensitive_log", "LOG")
    if record.classification == InformationClass.COMPANY_CONFIDENTIAL:
        return PolicyDecision(False, "deny_confidential_log", "LOG")
    if record.approval_status == ApprovalStatus.APPROVED and record.classification in {
        InformationClass.PUBLIC_COMPANY,
        InformationClass.PUBLIC_PROFESSIONAL,
    }:
        return PolicyDecision(True, "allow_public_log", "LOG")
    return PolicyDecision(False, "deny_log_by_default", "LOG")


def decide_training(record: IdentityFactRecord) -> PolicyDecision:
    """Training use is denied by default for all classes."""
    if record.classification is None:
        return PolicyDecision(False, "deny_missing_classification", AllowedUse.TRAINING_DATASET.value)
    if record.classification in {InformationClass.SECRET, InformationClass.FORGET_DELETE}:
        return PolicyDecision(False, "deny_secret_or_forget", AllowedUse.TRAINING_DATASET.value)
    if AllowedUse.TRAINING_DATASET in set(record.prohibited_uses or ()):
        return PolicyDecision(False, "deny_training_prohibited", AllowedUse.TRAINING_DATASET.value)
    # Even if intended, require a separate explicit authorization record beyond this foundation.
    return PolicyDecision(False, "deny_training_default", AllowedUse.TRAINING_DATASET.value)


def decide_delete_required(record: IdentityFactRecord) -> PolicyDecision:
    if record.classification == InformationClass.FORGET_DELETE:
        return PolicyDecision(True, "require_deletion_workflow", "DELETE")
    if (record.revocation_status or "").strip().lower() == "revoked":
        return PolicyDecision(True, "require_deletion_after_revocation", "DELETE")
    return PolicyDecision(False, "deletion_not_required", "DELETE")


def decide_can_approve(
    record: IdentityFactRecord,
    *,
    actor_id: str,
    consent: Optional[ConsentRecord] = None,
) -> PolicyDecision:
    if record.classification is None:
        return PolicyDecision(False, "deny_missing_classification", "APPROVE")
    if model_output_cannot_self_approve(record):
        return PolicyDecision(False, "deny_model_cannot_self_approve", "APPROVE")
    ok = can_person_approve(actor_id=actor_id, record=record, consent=consent)
    if ok:
        return PolicyDecision(True, "allow_approver", "APPROVE")
    return PolicyDecision(False, "deny_approver", "APPROVE")
