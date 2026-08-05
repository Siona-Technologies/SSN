"""Deterministic tests for hardened SIONA identity governance authorization."""

from __future__ import annotations

import json
import re
import unittest
from datetime import date
from pathlib import Path

from ssn.governance.consent import (
    SUBJECT_JAMES,
    SUBJECT_SAMSON,
    ConsentRecord,
    can_person_approve,
    delegation_allows,
    other_cofounder_cannot_approve_private,
    validate_consent,
)
from ssn.governance.identity_records import (
    IdentityFactRecord,
    inherit_strictest_classification,
    model_output_cannot_self_approve,
    validate_fact_record,
)
from ssn.governance.information_classes import (
    AllowedUse,
    ApprovalStatus,
    InformationClass,
    SubjectType,
)
from ssn.governance.policy import (
    PolicyContext,
    decide_can_approve,
    decide_delete_required,
    decide_draft_review,
    decide_embed,
    decide_log,
    decide_model_prompt,
    decide_owner_assistance,
    decide_public,
    decide_training,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "governance" / "public_identity_records.example.json"

SENSITIVE_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@gmail\.com", re.I),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"\b(api[_-]?key|password|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{16,}", re.I),
]


def _ctx(
    actor_id: str,
    *,
    authenticated: bool = True,
    verified_owner: bool = False,
    company_approvers: tuple = (),
) -> PolicyContext:
    return PolicyContext(
        actor_id=actor_id,
        actor_authenticated=authenticated,
        verified_owner=verified_owner,
        authorized_company_approver_ids=company_approvers,
    )


def _fact(**kwargs) -> IdentityFactRecord:
    defaults = dict(
        subject="Test Subject",
        subject_type=SubjectType.PERSON,
        classification=InformationClass.PUBLIC_PROFESSIONAL,
        statement="Test statement",
        source_type="test",
        source_reference="ssn/tests/test_identity_information_governance.py",
        approval_status=ApprovalStatus.DRAFT,
        approved_by="",
        approval_timestamp="",
        intended_uses=(AllowedUse.PUBLIC_RESPONSE,),
        prohibited_uses=(AllowedUse.TRAINING_DATASET,),
        review_date="2099-01-01",
        revocation_status="none",
        subject_id="person:test",
        personal_email="excluded",
        personal_phone="excluded",
        personal_address="excluded",
    )
    defaults.update(kwargs)
    return IdentityFactRecord(**defaults)


def _approved_public(**kwargs) -> IdentityFactRecord:
    base = dict(
        classification=InformationClass.PUBLIC_COMPANY,
        approval_status=ApprovalStatus.APPROVED,
        approved_by=SUBJECT_SAMSON,
        approval_timestamp="2026-08-05T00:00:00Z",
        review_date="2099-01-01",
        intended_uses=(AllowedUse.PUBLIC_RESPONSE, AllowedUse.PUBLIC_WEBSITE),
    )
    base.update(kwargs)
    return _fact(**base)


class TestIdentityInformationGovernance(unittest.TestCase):
    def test_missing_classification_denies_use(self):
        rec = _fact(classification=None)
        self.assertFalse(
            decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE).allowed
        )
        self.assertEqual(
            decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE).reason,
            "missing_classification",
        )

    def test_missing_approval_denies_public_use(self):
        rec = _fact(
            classification=InformationClass.PUBLIC_COMPANY,
            approval_status=ApprovalStatus.DRAFT,
            intended_uses=(AllowedUse.PUBLIC_RESPONSE,),
        )
        self.assertFalse(
            decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE).allowed
        )
        self.assertEqual(
            decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE).reason,
            "deny_not_approved",
        )

    def test_approved_public_without_requested_use_denied(self):
        rec = _approved_public(intended_uses=(AllowedUse.PUBLIC_WEBSITE,))
        d = decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE)
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_use_not_intended")

    def test_website_only_denied_for_response(self):
        rec = _approved_public(intended_uses=(AllowedUse.PUBLIC_WEBSITE,))
        self.assertFalse(
            decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE).allowed
        )
        self.assertTrue(
            decide_public(rec, requested_use=AllowedUse.PUBLIC_WEBSITE).allowed
        )

    def test_response_only_denied_for_website(self):
        rec = _approved_public(intended_uses=(AllowedUse.PUBLIC_RESPONSE,))
        self.assertFalse(
            decide_public(rec, requested_use=AllowedUse.PUBLIC_WEBSITE).allowed
        )
        self.assertTrue(
            decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE).allowed
        )

    def test_prohibited_public_use_denied(self):
        rec = _approved_public(
            intended_uses=(AllowedUse.PUBLIC_RESPONSE,),
            prohibited_uses=(AllowedUse.PUBLIC_RESPONSE, AllowedUse.TRAINING_DATASET),
        )
        d = decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE)
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_prohibited_use")

    def test_spoofed_requester_unauthenticated_denied(self):
        rec = _fact(
            classification=InformationClass.OWNER_PRIVATE,
            subject_id=SUBJECT_SAMSON,
            approval_status=ApprovalStatus.APPROVED,
            approved_by=SUBJECT_SAMSON,
            approval_timestamp="2026-08-05T00:00:00Z",
            intended_uses=(AllowedUse.OWNER_ASSISTANCE,),
        )
        d = decide_owner_assistance(
            rec,
            ctx=_ctx(SUBJECT_SAMSON, authenticated=False, verified_owner=True),
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_unauthenticated")

    def test_draft_owner_private_denied(self):
        rec = _fact(
            classification=InformationClass.OWNER_PRIVATE,
            subject_id=SUBJECT_SAMSON,
            approval_status=ApprovalStatus.DRAFT,
            intended_uses=(AllowedUse.OWNER_ASSISTANCE,),
        )
        d = decide_owner_assistance(
            rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True, verified_owner=True)
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_not_approved")

    def test_draft_cofounder_private_denied(self):
        rec = _fact(
            classification=InformationClass.COFOUNDER_PRIVATE,
            subject_id=SUBJECT_JAMES,
            approval_status=ApprovalStatus.DRAFT,
            intended_uses=(AllowedUse.OWNER_ASSISTANCE,),
        )
        d = decide_owner_assistance(
            rec, ctx=_ctx(SUBJECT_JAMES, authenticated=True, verified_owner=True)
        )
        self.assertFalse(d.allowed)

    def test_draft_review_does_not_permit_prompt(self):
        rec = _fact(
            classification=InformationClass.OWNER_PRIVATE,
            subject_id=SUBJECT_SAMSON,
            approval_status=ApprovalStatus.DRAFT,
            intended_uses=(AllowedUse.OWNER_ASSISTANCE, AllowedUse.MODEL_PROMPT),
        )
        ctx = _ctx(SUBJECT_SAMSON, authenticated=True, verified_owner=True)
        self.assertTrue(decide_draft_review(rec, ctx=ctx).allowed)
        self.assertFalse(decide_model_prompt(rec, ctx=ctx).allowed)
        self.assertFalse(decide_owner_assistance(rec, ctx=ctx).allowed)

    def test_owner_private_prompt_denied_without_auth_owner(self):
        rec = _fact(
            classification=InformationClass.OWNER_PRIVATE,
            subject_id=SUBJECT_SAMSON,
            approval_status=ApprovalStatus.APPROVED,
            approved_by=SUBJECT_SAMSON,
            approval_timestamp="2026-08-05T00:00:00Z",
            intended_uses=(AllowedUse.MODEL_PROMPT,),
        )
        self.assertFalse(
            decide_model_prompt(
                rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=False, verified_owner=True)
            ).allowed
        )
        self.assertFalse(
            decide_model_prompt(
                rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True, verified_owner=False)
            ).allowed
        )

    def test_model_prompt_intended_alone_insufficient(self):
        rec = _fact(
            classification=InformationClass.OWNER_PRIVATE,
            subject_id=SUBJECT_SAMSON,
            approval_status=ApprovalStatus.APPROVED,
            approved_by=SUBJECT_SAMSON,
            approval_timestamp="2026-08-05T00:00:00Z",
            intended_uses=(AllowedUse.MODEL_PROMPT,),
        )
        # Intended use present but wrong actor.
        d = decide_model_prompt(
            rec, ctx=_ctx(SUBJECT_JAMES, authenticated=True, verified_owner=True)
        )
        self.assertFalse(d.allowed)

    def test_cofounder_private_prompt_denied_without_subject_or_delegate(self):
        rec = _fact(
            classification=InformationClass.COFOUNDER_PRIVATE,
            subject_id=SUBJECT_JAMES,
            approval_status=ApprovalStatus.APPROVED,
            approved_by=SUBJECT_JAMES,
            approval_timestamp="2026-08-05T00:00:00Z",
            intended_uses=(AllowedUse.MODEL_PROMPT,),
        )
        d = decide_model_prompt(
            rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True, verified_owner=True)
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_missing_consent")

    def test_missing_consent_denies_delegated_access(self):
        rec = _fact(
            classification=InformationClass.COFOUNDER_PRIVATE,
            subject_id=SUBJECT_JAMES,
            approval_status=ApprovalStatus.APPROVED,
            approved_by=SUBJECT_JAMES,
            approval_timestamp="2026-08-05T00:00:00Z",
            intended_uses=(AllowedUse.OWNER_ASSISTANCE,),
        )
        d = decide_owner_assistance(
            rec,
            ctx=_ctx(SUBJECT_SAMSON, authenticated=True, verified_owner=True),
            consent=None,
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_missing_consent")

    def test_revoked_consent_denies_delegated_access(self):
        rec = _fact(
            classification=InformationClass.COFOUNDER_PRIVATE,
            subject_id=SUBJECT_JAMES,
            approval_status=ApprovalStatus.APPROVED,
            approved_by=SUBJECT_JAMES,
            approval_timestamp="2026-08-05T00:00:00Z",
            intended_uses=(AllowedUse.OWNER_ASSISTANCE,),
        )
        consent = ConsentRecord(
            subject_id=SUBJECT_JAMES,
            grantee_id=SUBJECT_SAMSON,
            allowed_uses=(AllowedUse.OWNER_ASSISTANCE,),
            granted=True,
            granted_by=SUBJECT_JAMES,
            timestamp="2026-08-05T00:00:00Z",
            revoked=True,
            revoked_at="2026-08-05T01:00:00Z",
        )
        d = decide_owner_assistance(
            rec,
            ctx=_ctx(SUBJECT_SAMSON, authenticated=True, verified_owner=True),
            consent=consent,
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_consent_revoked")

    def test_delegate_id_matching_is_exact(self):
        consent = ConsentRecord(
            subject_id=SUBJECT_JAMES,
            grantee_id=SUBJECT_SAMSON,
            allowed_uses=(AllowedUse.OWNER_ASSISTANCE,),
            granted=True,
            granted_by=SUBJECT_JAMES,
            timestamp="2026-08-05T00:00:00Z",
        )
        ok, _ = delegation_allows(
            consent, actor_id=SUBJECT_SAMSON, requested_use=AllowedUse.OWNER_ASSISTANCE
        )
        self.assertTrue(ok)
        ok2, reason = delegation_allows(
            consent,
            actor_id=SUBJECT_SAMSON + "-extra",
            requested_use=AllowedUse.OWNER_ASSISTANCE,
        )
        self.assertFalse(ok2)
        self.assertEqual(reason, "deny_delegate_mismatch")

    def test_prefix_substring_delegate_collision_denied(self):
        consent = ConsentRecord(
            subject_id=SUBJECT_JAMES,
            grantee_id=SUBJECT_SAMSON,
            allowed_uses=(AllowedUse.OWNER_ASSISTANCE,),
            granted=True,
            granted_by=SUBJECT_JAMES,
            timestamp="2026-08-05T00:00:00Z",
        )
        # Prefix of grantee must not match.
        ok, reason = delegation_allows(
            consent,
            actor_id="person:samson",
            requested_use=AllowedUse.OWNER_ASSISTANCE,
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "deny_delegate_mismatch")

    def test_consent_self_issued_by_delegate_denied(self):
        consent = ConsentRecord(
            subject_id=SUBJECT_JAMES,
            grantee_id=SUBJECT_SAMSON,
            allowed_uses=(AllowedUse.OWNER_ASSISTANCE,),
            granted=True,
            granted_by=SUBJECT_SAMSON,  # not the subject
            timestamp="2026-08-05T00:00:00Z",
        )
        ok, reason = validate_consent(consent)
        self.assertFalse(ok)
        self.assertEqual(reason, "deny_consent_not_subject_issued")

    def test_other_cofounder_cannot_approve_private(self):
        james_private = _fact(
            subject="James Ndodana Njaji",
            subject_id=SUBJECT_JAMES,
            classification=InformationClass.COFOUNDER_PRIVATE,
        )
        self.assertTrue(
            other_cofounder_cannot_approve_private(
                actor_id=SUBJECT_SAMSON, subject_id=SUBJECT_JAMES
            )
        )
        self.assertFalse(
            can_person_approve(
                actor_id=SUBJECT_SAMSON,
                actor_authenticated=True,
                record=james_private,
            )
        )
        decision = decide_can_approve(
            james_private, ctx=_ctx(SUBJECT_SAMSON, authenticated=True)
        )
        self.assertFalse(decision.allowed)

    def test_owner_assistance_consent_cannot_authorize_approval(self):
        rec = _fact(
            subject="James Ndodana Njaji",
            subject_id=SUBJECT_JAMES,
            classification=InformationClass.COFOUNDER_PRIVATE,
            approval_status=ApprovalStatus.DRAFT,
        )
        consent = ConsentRecord(
            subject_id=SUBJECT_JAMES,
            grantee_id=SUBJECT_SAMSON,
            allowed_uses=(AllowedUse.OWNER_ASSISTANCE,),
            granted=True,
            granted_by=SUBJECT_JAMES,
            timestamp="2026-08-05T00:00:00Z",
        )
        self.assertFalse(
            can_person_approve(
                actor_id=SUBJECT_SAMSON,
                actor_authenticated=True,
                record=rec,
                consent=consent,
            )
        )
        d = decide_can_approve(
            rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True), consent=consent
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_approval_use_not_delegated")

    def test_model_prompt_consent_cannot_authorize_approval(self):
        rec = _fact(
            subject="James Ndodana Njaji",
            subject_id=SUBJECT_JAMES,
            classification=InformationClass.COFOUNDER_PRIVATE,
        )
        consent = ConsentRecord(
            subject_id=SUBJECT_JAMES,
            grantee_id=SUBJECT_SAMSON,
            allowed_uses=(AllowedUse.MODEL_PROMPT,),
            granted=True,
            granted_by=SUBJECT_JAMES,
            timestamp="2026-08-05T00:00:00Z",
        )
        d = decide_can_approve(
            rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True), consent=consent
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_approval_use_not_delegated")

    def test_record_approval_consent_authorizes_exact_delegate(self):
        rec = _fact(
            subject="James Ndodana Njaji",
            subject_id=SUBJECT_JAMES,
            classification=InformationClass.COFOUNDER_PRIVATE,
        )
        consent = ConsentRecord(
            subject_id=SUBJECT_JAMES,
            grantee_id=SUBJECT_SAMSON,
            allowed_uses=(AllowedUse.RECORD_APPROVAL,),
            granted=True,
            granted_by=SUBJECT_JAMES,
            timestamp="2026-08-05T00:00:00Z",
        )
        d = decide_can_approve(
            rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True), consent=consent
        )
        self.assertTrue(d.allowed)
        self.assertEqual(d.reason, "allow_delegate_approve")

    def test_record_approval_delegate_matching_is_exact(self):
        rec = _fact(
            subject="James Ndodana Njaji",
            subject_id=SUBJECT_JAMES,
            classification=InformationClass.COFOUNDER_PRIVATE,
        )
        consent = ConsentRecord(
            subject_id=SUBJECT_JAMES,
            grantee_id=SUBJECT_SAMSON,
            allowed_uses=(AllowedUse.RECORD_APPROVAL,),
            granted=True,
            granted_by=SUBJECT_JAMES,
            timestamp="2026-08-05T00:00:00Z",
        )
        d = decide_can_approve(
            rec,
            ctx=_ctx(SUBJECT_SAMSON + "-assistant", authenticated=True),
            consent=consent,
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_delegate_mismatch")

    def test_consent_for_another_subject_cannot_authorize_approval(self):
        rec = _fact(
            subject="James Ndodana Njaji",
            subject_id=SUBJECT_JAMES,
            classification=InformationClass.COFOUNDER_PRIVATE,
        )
        consent = ConsentRecord(
            subject_id=SUBJECT_SAMSON,
            grantee_id="person:delegate",
            allowed_uses=(AllowedUse.RECORD_APPROVAL,),
            granted=True,
            granted_by=SUBJECT_SAMSON,
            timestamp="2026-08-05T00:00:00Z",
        )
        d = decide_can_approve(
            rec, ctx=_ctx("person:delegate", authenticated=True), consent=consent
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_consent_wrong_subject")

    def test_malformed_draft_cannot_be_approved(self):
        rec = _fact(statement="", classification=InformationClass.PUBLIC_COMPANY)
        d = decide_can_approve(rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True))
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_invalid_record")

    def test_missing_provenance_cannot_be_approved(self):
        rec = _fact(
            source_type="",
            source_reference="",
            subject_id=SUBJECT_SAMSON,
        )
        d = decide_can_approve(
            rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True)
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_invalid_record")

    def test_rejected_record_cannot_be_approved(self):
        rec = _fact(
            subject_id=SUBJECT_SAMSON,
            approval_status=ApprovalStatus.REJECTED,
        )
        d = decide_can_approve(rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True))
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_rejected")

    def test_revoked_approval_status_cannot_be_approved(self):
        rec = _fact(
            subject_id=SUBJECT_SAMSON,
            approval_status=ApprovalStatus.REVOKED,
            approved_by=SUBJECT_SAMSON,
            approval_timestamp="2026-01-01T00:00:00Z",
        )
        d = decide_can_approve(rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True))
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_revoked")

    def test_expired_record_cannot_be_approved(self):
        rec = _fact(
            subject_id=SUBJECT_SAMSON,
            approval_status=ApprovalStatus.EXPIRED,
            approved_by=SUBJECT_SAMSON,
            approval_timestamp="2026-01-01T00:00:00Z",
            review_date="2020-01-01",
        )
        d = decide_can_approve(rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True))
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_expired")

    def test_revocation_status_revoked_cannot_be_approved(self):
        rec = _fact(
            subject_id=SUBJECT_SAMSON,
            approval_status=ApprovalStatus.DRAFT,
            revocation_status="revoked",
        )
        d = decide_can_approve(rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True))
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_revoked")

    def test_invalid_consent_timestamp_denied(self):
        consent = ConsentRecord(
            subject_id=SUBJECT_JAMES,
            grantee_id=SUBJECT_SAMSON,
            allowed_uses=(AllowedUse.RECORD_APPROVAL,),
            granted=True,
            granted_by=SUBJECT_JAMES,
            timestamp="not-a-timestamp",
        )
        ok, reason = validate_consent(consent)
        self.assertFalse(ok)
        self.assertEqual(reason, "invalid_consent_timestamp")
        rec = _fact(
            subject_id=SUBJECT_JAMES,
            classification=InformationClass.COFOUNDER_PRIVATE,
        )
        d = decide_can_approve(
            rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True), consent=consent
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "invalid_consent_timestamp")

    def test_invalid_consent_revoked_at_denied(self):
        consent = ConsentRecord(
            subject_id=SUBJECT_JAMES,
            grantee_id=SUBJECT_SAMSON,
            allowed_uses=(AllowedUse.RECORD_APPROVAL,),
            granted=True,
            granted_by=SUBJECT_JAMES,
            timestamp="2026-08-05T00:00:00Z",
            revoked=True,
            revoked_at="sometime",
        )
        ok, reason = validate_consent(consent)
        self.assertFalse(ok)
        self.assertEqual(reason, "invalid_consent_revoked_at")

    def test_subject_may_approve_own_valid_draft(self):
        rec = _fact(
            subject_id=SUBJECT_SAMSON,
            classification=InformationClass.OWNER_PRIVATE,
            approval_status=ApprovalStatus.DRAFT,
        )
        d = decide_can_approve(rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True))
        self.assertTrue(d.allowed)
        self.assertEqual(d.reason, "allow_subject_approve")

    def test_secret_and_forget_delete_unapprovable(self):
        for cls, reason in (
            (InformationClass.SECRET, "deny_secret"),
            (InformationClass.FORGET_DELETE, "deny_forget_delete"),
        ):
            rec = _fact(classification=cls, subject_id=SUBJECT_SAMSON)
            d = decide_can_approve(rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True))
            self.assertFalse(d.allowed, cls)
            self.assertEqual(d.reason, reason, cls)

    def test_arbitrary_actor_cannot_approve_company_public_legal(self):
        for cls in (
            InformationClass.PUBLIC_COMPANY,
            InformationClass.COMPANY_CONFIDENTIAL,
            InformationClass.LEGAL_RESTRICTED,
        ):
            rec = _fact(classification=cls, subject_id="company:siona-technologies")
            d = decide_can_approve(
                rec, ctx=_ctx("person:random-actor", authenticated=True)
            )
            self.assertFalse(d.allowed, cls)

    def test_authorized_company_approver_can_approve(self):
        rec = _fact(
            classification=InformationClass.PUBLIC_COMPANY,
            subject_id="company:siona-technologies",
            approval_status=ApprovalStatus.DRAFT,
        )
        d = decide_can_approve(
            rec,
            ctx=_ctx(
                SUBJECT_SAMSON,
                authenticated=True,
                company_approvers=(SUBJECT_SAMSON,),
            ),
        )
        self.assertTrue(d.allowed)
        self.assertEqual(d.reason, "allow_company_approver")

    def test_invalid_review_date_denies_use(self):
        rec = _approved_public(review_date="not-a-date")
        d = decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE)
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "invalid_review_date")

    def test_invalid_approval_timestamp_denies_use(self):
        rec = _approved_public(approval_timestamp="yesterday")
        d = decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE)
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "invalid_approval_timestamp")

    def test_unknown_revocation_status_denies_use(self):
        rec = _approved_public(revocation_status="maybe")
        d = decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE)
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "invalid_revocation_status")

    def test_malformed_approved_record_denied(self):
        rec = _approved_public(approved_by="")
        d = decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE)
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_invalid_record")

    def test_approval_status_revoked_requires_deletion(self):
        rec = _fact(
            classification=InformationClass.PUBLIC_COMPANY,
            approval_status=ApprovalStatus.REVOKED,
            approved_by=SUBJECT_SAMSON,
            approval_timestamp="2026-01-01T00:00:00Z",
            review_date="2099-01-01",
        )
        self.assertTrue(decide_delete_required(rec).allowed)

    def test_secret_remains_denied_everywhere(self):
        rec = _fact(
            classification=InformationClass.SECRET,
            approval_status=ApprovalStatus.APPROVED,
            approved_by=SUBJECT_SAMSON,
            approval_timestamp="2026-08-05T00:00:00Z",
            intended_uses=tuple(AllowedUse),
        )
        ctx = _ctx(SUBJECT_SAMSON, authenticated=True, verified_owner=True)
        self.assertFalse(decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE).allowed)
        self.assertFalse(decide_model_prompt(rec, ctx=ctx).allowed)
        self.assertFalse(decide_embed(rec).allowed)
        self.assertFalse(decide_log(rec).allowed)
        self.assertFalse(decide_training(rec).allowed)
        self.assertFalse(decide_owner_assistance(rec, ctx=ctx).allowed)

    def test_forget_delete_denied_and_requires_deletion(self):
        rec = _fact(classification=InformationClass.FORGET_DELETE)
        self.assertFalse(
            decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE).allowed
        )
        self.assertTrue(decide_delete_required(rec).allowed)

    def test_training_denied_by_default(self):
        for cls in InformationClass:
            if cls is InformationClass.SECRET:
                continue
            rec = _fact(
                classification=cls,
                approval_status=ApprovalStatus.APPROVED,
                approved_by=SUBJECT_SAMSON,
                approval_timestamp="2026-01-01T00:00:00Z",
                intended_uses=(AllowedUse.TRAINING_DATASET,),
                prohibited_uses=(),
            )
            self.assertFalse(decide_training(rec).allowed, cls)

    def test_revoked_records_deny_use(self):
        rec = _approved_public(revocation_status="revoked")
        self.assertFalse(
            decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE).allowed
        )
        self.assertTrue(decide_delete_required(rec).allowed)

    def test_expired_approval_denies_use(self):
        rec = _approved_public(review_date="2020-06-01")
        d = decide_public(
            rec, requested_use=AllowedUse.PUBLIC_RESPONSE, today=date(2026, 8, 5)
        )
        self.assertFalse(d.allowed)
        self.assertEqual(d.reason, "deny_expired")

    def test_owner_private_assistance_when_approved(self):
        rec = _fact(
            classification=InformationClass.OWNER_PRIVATE,
            subject_id=SUBJECT_SAMSON,
            approval_status=ApprovalStatus.APPROVED,
            approved_by=SUBJECT_SAMSON,
            approval_timestamp="2026-08-05T00:00:00Z",
            intended_uses=(AllowedUse.OWNER_ASSISTANCE,),
        )
        self.assertTrue(
            decide_owner_assistance(
                rec, ctx=_ctx(SUBJECT_SAMSON, authenticated=True, verified_owner=True)
            ).allowed
        )

    def test_valid_delegate_access(self):
        rec = _fact(
            classification=InformationClass.COFOUNDER_PRIVATE,
            subject_id=SUBJECT_JAMES,
            approval_status=ApprovalStatus.APPROVED,
            approved_by=SUBJECT_JAMES,
            approval_timestamp="2026-08-05T00:00:00Z",
            intended_uses=(AllowedUse.OWNER_ASSISTANCE,),
        )
        consent = ConsentRecord(
            subject_id=SUBJECT_JAMES,
            grantee_id=SUBJECT_SAMSON,
            allowed_uses=(AllowedUse.OWNER_ASSISTANCE,),
            granted=True,
            granted_by=SUBJECT_JAMES,
            timestamp="2026-08-05T00:00:00Z",
        )
        d = decide_owner_assistance(
            rec,
            ctx=_ctx(SUBJECT_SAMSON, authenticated=True, verified_owner=True),
            consent=consent,
        )
        self.assertTrue(d.allowed)

    def test_derived_information_inherits_strictest_classification(self):
        derived = inherit_strictest_classification(
            [
                InformationClass.PUBLIC_COMPANY,
                InformationClass.OWNER_PRIVATE,
                InformationClass.SECRET,
            ]
        )
        self.assertEqual(derived, InformationClass.SECRET)

    def test_model_generated_content_cannot_approve_itself(self):
        rec = _approved_public(source_type="model_output", approved_by="model")
        self.assertTrue(model_output_cannot_self_approve(rec))
        self.assertFalse(
            decide_public(rec, requested_use=AllowedUse.PUBLIC_RESPONSE).allowed
        )

    def test_legal_restricted_cannot_enter_ordinary_memory(self):
        rec = _fact(
            classification=InformationClass.LEGAL_RESTRICTED,
            approval_status=ApprovalStatus.APPROVED,
            approved_by=SUBJECT_SAMSON,
            approval_timestamp="2026-08-05T00:00:00Z",
            intended_uses=(AllowedUse.OWNER_ASSISTANCE, AllowedUse.MODEL_PROMPT),
        )
        ctx = _ctx(SUBJECT_SAMSON, authenticated=True, verified_owner=True)
        self.assertFalse(decide_owner_assistance(rec, ctx=ctx).allowed)
        self.assertFalse(decide_model_prompt(rec, ctx=ctx).allowed)

    def test_example_seed_records_are_non_sensitive(self):
        self.assertTrue(EXAMPLE.is_file())
        raw = EXAMPLE.read_text(encoding="utf-8")
        for pattern in SENSITIVE_PATTERNS:
            self.assertIsNone(pattern.search(raw), pattern.pattern)
        data = json.loads(raw)
        self.assertIn("DRAFT/EXAMPLE", data["_label"])
        self.assertEqual(data["_privacy"]["personal_email"], "excluded")
        self.assertFalse(data["_privacy"]["chatgpt_history_imported"])
        self.assertFalse(data["_privacy"]["private_cofounder_data_included"])
        for rec in data["records"]:
            self.assertEqual(rec["personal_email"], "excluded")
            self.assertEqual(rec["personal_phone"], "excluded")
            self.assertNotIn("@", rec.get("statement", ""))

    def test_validate_fact_record_rejects_embedded_email_marker(self):
        rec = _fact(personal_email="someone@example.com")
        ok, reason = validate_fact_record(rec)
        self.assertFalse(ok)
        self.assertEqual(reason, "personal_email_must_be_excluded")

    def test_no_ssn_data_dependency(self):
        data_dir = ROOT / "ssn" / "data"
        before = sorted(p.name for p in data_dir.iterdir()) if data_dir.is_dir() else []
        _ = decide_public(
            _approved_public(), requested_use=AllowedUse.PUBLIC_RESPONSE
        )
        after = sorted(p.name for p in data_dir.iterdir()) if data_dir.is_dir() else []
        self.assertEqual(before, after)

    def test_consent_revocation_requires_deletion_signal(self):
        consent = ConsentRecord(
            subject_id=SUBJECT_JAMES,
            grantee_id=SUBJECT_SAMSON,
            allowed_uses=(AllowedUse.OWNER_ASSISTANCE,),
            granted=False,
            granted_by=SUBJECT_JAMES,
            timestamp="2026-08-05T00:00:00Z",
            revoked=True,
            revoked_at="2026-08-05T01:00:00Z",
        )
        rec = _fact(classification=InformationClass.COFOUNDER_PRIVATE, subject_id=SUBJECT_JAMES)
        self.assertTrue(decide_delete_required(rec, consent=consent).allowed)


class TestIdentityGovernanceDocs(unittest.TestCase):
    def test_governance_docs_exist_and_state_boundaries(self):
        docs = {
            "SIONA_IDENTITY_INFORMATION_GOVERNANCE.md",
            "SIONA_INFORMATION_CLASSIFICATION.md",
            "SIONA_CONSENT_AND_REVOCATION.md",
            "SIONA_PUBLIC_PROFILE_POLICY.md",
            "SIONA_PRIVATE_CONTEXT_POLICY.md",
            "SIONA_WEBSITE_CONTENT_AUDIT_PLAN.md",
        }
        for name in docs:
            self.assertTrue((ROOT / "docs" / name).is_file(), name)
        identity = (ROOT / "docs" / "SIONA_IDENTITY_INFORMATION_GOVERNANCE.md").read_text(
            encoding="utf-8"
        )
        public = (ROOT / "docs" / "SIONA_PUBLIC_PROFILE_POLICY.md").read_text(encoding="utf-8")
        consent = (ROOT / "docs" / "SIONA_CONSENT_AND_REVOCATION.md").read_text(
            encoding="utf-8"
        )
        private = (ROOT / "docs" / "SIONA_PRIVATE_CONTEXT_POLICY.md").read_text(
            encoding="utf-8"
        )
        website = (ROOT / "docs" / "SIONA_WEBSITE_CONTENT_AUDIT_PLAN.md").read_text(
            encoding="utf-8"
        )
        status = (ROOT / "docs" / "PHASE_STATUS.md").read_text(encoding="utf-8")
        adr = (ROOT / "docs" / "adr" / "0003-first-local-model-strategy.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("SIONA Technologies", identity)
        self.assertIn("PolicyContext", consent)
        self.assertIn("actor_authenticated", consent)
        self.assertIn("grantee_id", consent)
        self.assertIn("RECORD_APPROVAL", consent)
        self.assertIn("never interchangeable", consent.lower())
        self.assertIn("exact", consent.lower())
        self.assertIn("personal_email: excluded", public)
        self.assertIn("APPROVED", private)
        self.assertIn("RECORD_APPROVAL", private)
        self.assertIn("Audit **sionaglobal.com** only", website)
        self.assertIn("in progress", status.lower())
        self.assertIn("Phase 4 remains **not started**", status)
        self.assertIn("inactive", status.lower())
        self.assertRegex(adr.replace("\r\n", "\n"), r"(?m)^## Status\n\nProposed\n")
        combined = "\n".join([identity, public, consent, private, website])
        self.assertNotRegex(
            combined, r"[A-Za-z0-9._%+-]+@gmail\.com", msg="no personal gmail"
        )
        self.assertIn("not** an assistant, chatbot", identity.lower())


if __name__ == "__main__":
    unittest.main()
