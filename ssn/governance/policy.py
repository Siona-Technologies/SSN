"""Deterministic information-use policy decisions (deny by default)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional, Tuple

from ssn.governance.consent import (
    ConsentRecord,
    can_person_approve,
    consent_revoked,
    delegation_allows,
    is_model_identity,
    validate_consent,
)
from ssn.governance.identity_records import (
    IdentityFactRecord,
    model_output_cannot_self_approve,
    parse_iso_date,
    validate_fact_record,
)
from ssn.governance.information_classes import (
    AllowedUse,
    ApprovalStatus,
    InformationClass,
)

_PUBLIC_USES = frozenset({AllowedUse.PUBLIC_WEBSITE, AllowedUse.PUBLIC_RESPONSE})


@dataclass(frozen=True)
class PolicyContext:
    """Trusted authorization context. Actor ID alone never authenticates."""

    actor_id: str
    actor_authenticated: bool
    verified_owner: bool
    authorized_company_approver_ids: Tuple[str, ...] = ()


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    use: str = ""


def _use_intended(record: IdentityFactRecord, use: AllowedUse) -> bool:
    return use in tuple(record.intended_uses or ())


def _use_prohibited(record: IdentityFactRecord, use: AllowedUse) -> bool:
    return use in tuple(record.prohibited_uses or ())


def _expiry_state(
    record: IdentityFactRecord, *, today: Optional[date] = None
) -> Tuple[Optional[bool], str]:
    """
    Returns (expired?, reason).
    expired True → deny_expired
    expired False → ok
    expired None → invalid date / denial reason in second value
    """
    if record.approval_status == ApprovalStatus.EXPIRED:
        return True, "deny_expired"
    if record.approval_status != ApprovalStatus.APPROVED:
        # Non-approved paths handle their own status; date may still be present.
        if not (record.review_date or "").strip():
            return False, "ok"
    review, reason = parse_iso_date(record.review_date)
    if review is None:
        # APPROVED already validated; any remaining invalid date is fail-closed.
        return None, "invalid_review_date"
    now = today or date.today()
    if now > review:
        return True, "deny_expired"
    return False, "ok"


def _base_denial(
    record: IdentityFactRecord, *, today: Optional[date] = None
) -> Optional[PolicyDecision]:
    ok, reason = validate_fact_record(record)
    if not ok:
        # Map validation reasons into stable policy reasons.
        if reason in {
            "invalid_approval_timestamp",
            "invalid_review_date",
            "invalid_revocation_status",
            "deny_invalid_record",
            "missing_classification",
        }:
            return PolicyDecision(False, reason)
        return PolicyDecision(False, "deny_invalid_record")

    if record.classification is None:
        return PolicyDecision(False, "deny_missing_classification")
    if record.classification == InformationClass.SECRET:
        return PolicyDecision(False, "deny_secret")
    if record.classification == InformationClass.FORGET_DELETE:
        return PolicyDecision(False, "deny_forget_delete")

    rev = (record.revocation_status or "").strip().lower()
    if rev == "revoked":
        return PolicyDecision(False, "deny_revoked")
    if record.approval_status == ApprovalStatus.REVOKED:
        return PolicyDecision(False, "deny_revoked")
    if record.approval_status == ApprovalStatus.REJECTED:
        return PolicyDecision(False, "deny_rejected")

    expired, exp_reason = _expiry_state(record, today=today)
    if expired is None:
        return PolicyDecision(False, exp_reason)
    if expired:
        return PolicyDecision(False, "deny_expired")

    if model_output_cannot_self_approve(record):
        return PolicyDecision(False, "deny_model_cannot_self_approve")
    return None


def _require_auth(ctx: PolicyContext) -> Optional[PolicyDecision]:
    if not ctx.actor_authenticated:
        return PolicyDecision(False, "deny_unauthenticated")
    if not (ctx.actor_id or "").strip():
        return PolicyDecision(False, "deny_unauthenticated")
    if is_model_identity(ctx.actor_id):
        return PolicyDecision(False, "deny_model_identity")
    return None


def decide_public(
    record: IdentityFactRecord,
    *,
    requested_use: AllowedUse,
    today: Optional[date] = None,
) -> PolicyDecision:
    use_name = requested_use.value if isinstance(requested_use, AllowedUse) else str(requested_use)
    if requested_use not in _PUBLIC_USES:
        return PolicyDecision(False, "deny_not_public_use", use_name)

    denied = _base_denial(record, today=today)
    if denied:
        return PolicyDecision(denied.allowed, denied.reason, use_name)

    if record.classification not in {
        InformationClass.PUBLIC_COMPANY,
        InformationClass.PUBLIC_PROFESSIONAL,
    }:
        return PolicyDecision(False, "deny_not_public_class", use_name)
    if record.approval_status != ApprovalStatus.APPROVED:
        return PolicyDecision(False, "deny_not_approved", use_name)
    if _use_prohibited(record, requested_use):
        return PolicyDecision(False, "deny_prohibited_use", use_name)
    if not _use_intended(record, requested_use):
        return PolicyDecision(False, "deny_use_not_intended", use_name)
    return PolicyDecision(True, "allow_public_approved", use_name)


def decide_draft_review(
    record: IdentityFactRecord,
    *,
    ctx: PolicyContext,
) -> PolicyDecision:
    """
    Narrow draft-review gate: authenticated subject may review their own DRAFT.
    Does not authorize prompting, retrieval, logging, or normal assistance.
    """
    auth = _require_auth(ctx)
    if auth:
        return PolicyDecision(auth.allowed, auth.reason, "DRAFT_REVIEW")
    ok, reason = validate_fact_record(record)
    if not ok:
        return PolicyDecision(False, reason if reason.startswith("invalid_") or reason.startswith("deny_") or reason.startswith("missing_") else "deny_invalid_record", "DRAFT_REVIEW")
    if record.approval_status != ApprovalStatus.DRAFT:
        return PolicyDecision(False, "deny_not_draft", "DRAFT_REVIEW")
    if (ctx.actor_id or "").strip() != (record.subject_id or "").strip():
        return PolicyDecision(False, "deny_wrong_subject", "DRAFT_REVIEW")
    return PolicyDecision(True, "allow_draft_review_only", "DRAFT_REVIEW")


def decide_owner_assistance(
    record: IdentityFactRecord,
    *,
    ctx: PolicyContext,
    consent: Optional[ConsentRecord] = None,
    today: Optional[date] = None,
) -> PolicyDecision:
    use = AllowedUse.OWNER_ASSISTANCE
    denied = _base_denial(record, today=today)
    if denied:
        return PolicyDecision(denied.allowed, denied.reason, use.value)

    auth = _require_auth(ctx)
    if auth:
        return PolicyDecision(auth.allowed, auth.reason, use.value)

    cls = record.classification
    assert cls is not None
    actor = (ctx.actor_id or "").strip()
    subject = (record.subject_id or "").strip()

    if cls == InformationClass.LEGAL_RESTRICTED:
        return PolicyDecision(False, "deny_legal_not_ordinary_memory", use.value)

    if cls == InformationClass.OWNER_PRIVATE:
        if record.approval_status != ApprovalStatus.APPROVED:
            return PolicyDecision(False, "deny_not_approved", use.value)
        if not ctx.verified_owner:
            return PolicyDecision(False, "deny_guest_owner_private", use.value)
        if actor != subject:
            return PolicyDecision(False, "deny_wrong_owner_subject", use.value)
        if _use_prohibited(record, use):
            return PolicyDecision(False, "deny_prohibited_use", use.value)
        if not _use_intended(record, use):
            return PolicyDecision(False, "deny_use_not_intended", use.value)
        return PolicyDecision(True, "allow_owner_private", use.value)

    if cls == InformationClass.COFOUNDER_PRIVATE:
        if record.approval_status != ApprovalStatus.APPROVED:
            return PolicyDecision(False, "deny_not_approved", use.value)
        if _use_prohibited(record, use):
            return PolicyDecision(False, "deny_prohibited_use", use.value)
        if not _use_intended(record, use):
            return PolicyDecision(False, "deny_use_not_intended", use.value)
        if actor == subject:
            return PolicyDecision(True, "allow_cofounder_subject", use.value)
        ok, reason = delegation_allows(consent, actor_id=actor, requested_use=use)
        if not ok:
            return PolicyDecision(False, reason, use.value)
        if consent is None or consent.subject_id != subject:
            return PolicyDecision(False, "deny_missing_consent", use.value)
        return PolicyDecision(True, "allow_cofounder_delegate", use.value)

    if cls == InformationClass.COMPANY_CONFIDENTIAL:
        if record.approval_status != ApprovalStatus.APPROVED:
            return PolicyDecision(False, "deny_not_approved", use.value)
        if not (ctx.verified_owner or actor in set(ctx.authorized_company_approver_ids)):
            return PolicyDecision(False, "deny_guest_confidential", use.value)
        if _use_prohibited(record, use):
            return PolicyDecision(False, "deny_prohibited_use", use.value)
        if not _use_intended(record, use):
            return PolicyDecision(False, "deny_use_not_intended", use.value)
        return PolicyDecision(True, "allow_owner_confidential", use.value)

    if cls in {InformationClass.PUBLIC_COMPANY, InformationClass.PUBLIC_PROFESSIONAL}:
        # Assistance may surface approved public facts when PUBLIC_RESPONSE intended.
        pub = decide_public(record, requested_use=AllowedUse.PUBLIC_RESPONSE, today=today)
        if pub.allowed:
            return PolicyDecision(True, "allow_public_for_owner", use.value)
        return PolicyDecision(False, pub.reason, use.value)

    return PolicyDecision(False, "deny_by_default", use.value)


def decide_model_prompt(
    record: IdentityFactRecord,
    *,
    ctx: PolicyContext,
    consent: Optional[ConsentRecord] = None,
    today: Optional[date] = None,
) -> PolicyDecision:
    use = AllowedUse.MODEL_PROMPT
    denied = _base_denial(record, today=today)
    if denied:
        return PolicyDecision(denied.allowed, denied.reason, use.value)

    cls = record.classification
    assert cls is not None

    if cls in {
        InformationClass.SECRET,
        InformationClass.FORGET_DELETE,
        InformationClass.LEGAL_RESTRICTED,
    }:
        return PolicyDecision(False, "deny_restricted_prompt", use.value)

    if _use_prohibited(record, use):
        return PolicyDecision(False, "deny_prohibited_use", use.value)
    if not _use_intended(record, use):
        return PolicyDecision(False, "deny_use_not_intended", use.value)

    # Intended use alone is never enough — class-specific auth follows.
    if cls in {InformationClass.PUBLIC_COMPANY, InformationClass.PUBLIC_PROFESSIONAL}:
        if record.approval_status != ApprovalStatus.APPROVED:
            return PolicyDecision(False, "deny_not_approved_for_prompt", use.value)
        return PolicyDecision(True, "allow_approved_public_prompt", use.value)

    auth = _require_auth(ctx)
    if auth:
        return PolicyDecision(auth.allowed, auth.reason, use.value)

    actor = (ctx.actor_id or "").strip()
    subject = (record.subject_id or "").strip()

    if record.approval_status != ApprovalStatus.APPROVED:
        return PolicyDecision(False, "deny_not_approved_for_prompt", use.value)

    if cls == InformationClass.OWNER_PRIVATE:
        if not ctx.verified_owner or actor != subject:
            return PolicyDecision(False, "deny_owner_prompt_unauthorized", use.value)
        return PolicyDecision(True, "allow_owner_private_prompt", use.value)

    if cls == InformationClass.COFOUNDER_PRIVATE:
        if actor == subject:
            return PolicyDecision(True, "allow_cofounder_subject_prompt", use.value)
        ok, reason = delegation_allows(consent, actor_id=actor, requested_use=use)
        if not ok:
            return PolicyDecision(False, reason, use.value)
        if consent is None or consent.subject_id != subject:
            return PolicyDecision(False, "deny_missing_consent", use.value)
        return PolicyDecision(True, "allow_cofounder_delegate_prompt", use.value)

    if cls == InformationClass.COMPANY_CONFIDENTIAL:
        if not (
            ctx.verified_owner or actor in set(ctx.authorized_company_approver_ids)
        ):
            return PolicyDecision(False, "deny_confidential_prompt_unauthorized", use.value)
        return PolicyDecision(True, "allow_confidential_prompt", use.value)

    return PolicyDecision(False, "deny_by_default", use.value)


def decide_embed(
    record: IdentityFactRecord,
    *,
    today: Optional[date] = None,
) -> PolicyDecision:
    use = AllowedUse.RETRIEVAL
    denied = _base_denial(record, today=today)
    if denied:
        return PolicyDecision(denied.allowed, denied.reason, use.value)
    if record.classification in {
        InformationClass.SECRET,
        InformationClass.FORGET_DELETE,
        InformationClass.LEGAL_RESTRICTED,
        InformationClass.OWNER_PRIVATE,
        InformationClass.COFOUNDER_PRIVATE,
        InformationClass.COMPANY_CONFIDENTIAL,
    }:
        return PolicyDecision(False, "deny_restricted_embed", use.value)
    if _use_prohibited(record, use):
        return PolicyDecision(False, "deny_prohibited_use", use.value)
    if not _use_intended(record, use):
        return PolicyDecision(False, "deny_use_not_intended", use.value)
    if record.classification in {
        InformationClass.PUBLIC_COMPANY,
        InformationClass.PUBLIC_PROFESSIONAL,
    } and record.approval_status == ApprovalStatus.APPROVED:
        return PolicyDecision(True, "allow_approved_public_embed", use.value)
    return PolicyDecision(False, "deny_embed_by_default", use.value)


def decide_log(
    record: IdentityFactRecord,
    *,
    today: Optional[date] = None,
) -> PolicyDecision:
    denied = _base_denial(record, today=today)
    if denied:
        return PolicyDecision(denied.allowed, denied.reason, "LOG")
    if record.classification in {
        InformationClass.SECRET,
        InformationClass.FORGET_DELETE,
        InformationClass.LEGAL_RESTRICTED,
        InformationClass.OWNER_PRIVATE,
        InformationClass.COFOUNDER_PRIVATE,
        InformationClass.COMPANY_CONFIDENTIAL,
    }:
        return PolicyDecision(False, "deny_sensitive_log", "LOG")
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
    return PolicyDecision(False, "deny_training_default", AllowedUse.TRAINING_DATASET.value)


def decide_delete_required(
    record: IdentityFactRecord,
    *,
    consent: Optional[ConsentRecord] = None,
) -> PolicyDecision:
    if record.classification == InformationClass.FORGET_DELETE:
        return PolicyDecision(True, "require_deletion_workflow", "DELETE")
    if (record.revocation_status or "").strip().lower() == "revoked":
        return PolicyDecision(True, "require_deletion_after_revocation", "DELETE")
    if record.approval_status == ApprovalStatus.REVOKED:
        return PolicyDecision(True, "require_deletion_after_revocation", "DELETE")
    if consent is not None and consent_revoked(consent):
        return PolicyDecision(True, "require_deletion_after_consent_revocation", "DELETE")
    return PolicyDecision(False, "deletion_not_required", "DELETE")


def decide_can_approve(
    record: IdentityFactRecord,
    *,
    ctx: PolicyContext,
    consent: Optional[ConsentRecord] = None,
) -> PolicyDecision:
    """
    Approve a valid DRAFT record only.

    Rejected, expired, or revoked records must be replaced by a new DRAFT
    revision — this function never silently reactivates them.
    """
    ok, reason = validate_fact_record(record)
    if not ok:
        if reason in {
            "invalid_approval_timestamp",
            "invalid_review_date",
            "invalid_revocation_status",
            "deny_invalid_record",
            "missing_classification",
        }:
            mapped = (
                "deny_missing_classification"
                if reason == "missing_classification"
                else reason
            )
            return PolicyDecision(False, mapped, "APPROVE")
        return PolicyDecision(False, "deny_invalid_record", "APPROVE")

    if record.classification is None:
        return PolicyDecision(False, "deny_missing_classification", "APPROVE")
    if model_output_cannot_self_approve(record):
        return PolicyDecision(False, "deny_model_cannot_self_approve", "APPROVE")
    if record.classification == InformationClass.SECRET:
        return PolicyDecision(False, "deny_secret", "APPROVE")
    if record.classification == InformationClass.FORGET_DELETE:
        return PolicyDecision(False, "deny_forget_delete", "APPROVE")

    rev = (record.revocation_status or "").strip().lower()
    if rev == "revoked":
        return PolicyDecision(False, "deny_revoked", "APPROVE")
    if record.approval_status == ApprovalStatus.REVOKED:
        return PolicyDecision(False, "deny_revoked", "APPROVE")
    if record.approval_status == ApprovalStatus.REJECTED:
        return PolicyDecision(False, "deny_rejected", "APPROVE")
    if record.approval_status == ApprovalStatus.EXPIRED:
        return PolicyDecision(False, "deny_expired", "APPROVE")
    if record.approval_status != ApprovalStatus.DRAFT:
        return PolicyDecision(False, "deny_not_draft", "APPROVE")

    auth = _require_auth(ctx)
    if auth:
        return PolicyDecision(auth.allowed, auth.reason, "APPROVE")

    actor = (ctx.actor_id or "").strip()
    subject = (record.subject_id or "").strip()

    # Subject self-approval of their own valid DRAFT.
    if subject and actor == subject:
        return PolicyDecision(True, "allow_subject_approve", "APPROVE")

    # Exact authorized company approver for company/public/legal drafts.
    if record.classification in {
        InformationClass.PUBLIC_COMPANY,
        InformationClass.PUBLIC_PROFESSIONAL,
        InformationClass.COMPANY_CONFIDENTIAL,
        InformationClass.LEGAL_RESTRICTED,
    } and actor in set(ctx.authorized_company_approver_ids or ()):
        return PolicyDecision(True, "allow_company_approver", "APPROVE")

    # Delegated approval: RECORD_APPROVAL only (never assistance/prompt substitutes).
    if consent is None:
        return PolicyDecision(False, "deny_approver", "APPROVE")

    vok, vreason = validate_consent(consent)
    if not vok:
        return PolicyDecision(False, vreason, "APPROVE")
    if consent_revoked(consent):
        return PolicyDecision(False, "deny_consent_revoked", "APPROVE")
    if (consent.subject_id or "").strip() != subject:
        return PolicyDecision(False, "deny_consent_wrong_subject", "APPROVE")
    if actor != (consent.grantee_id or "").strip():
        return PolicyDecision(False, "deny_delegate_mismatch", "APPROVE")
    if AllowedUse.RECORD_APPROVAL not in consent.allowed_uses:
        return PolicyDecision(False, "deny_approval_use_not_delegated", "APPROVE")

    ok_auth = can_person_approve(
        actor_id=ctx.actor_id,
        actor_authenticated=ctx.actor_authenticated,
        record=record,
        authorized_company_approver_ids=ctx.authorized_company_approver_ids,
        consent=consent,
    )
    if ok_auth:
        return PolicyDecision(True, "allow_delegate_approve", "APPROVE")
    return PolicyDecision(False, "deny_approver", "APPROVE")
