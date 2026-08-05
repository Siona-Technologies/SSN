"""Deterministic tests for SIONA identity and information governance."""

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
    other_cofounder_cannot_approve_private,
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
    decide_can_approve,
    decide_delete_required,
    decide_embed,
    decide_log,
    decide_model_prompt,
    decide_owner_assistance,
    decide_public,
    decide_training,
)

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "governance" / "public_identity_records.example.json"

# Do not use broad digit patterns that false-positive on ISO dates.
SENSITIVE_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@gmail\.com", re.I),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
    re.compile(r"(api[_-]?key|password|secret|token)\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}", re.I),
]


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


class TestIdentityInformationGovernance(unittest.TestCase):
    def test_missing_classification_denies_use(self):
        rec = _fact(classification=None)
        self.assertFalse(decide_public(rec).allowed)
        self.assertEqual(decide_public(rec).reason, "deny_missing_classification")
        self.assertFalse(decide_model_prompt(rec).allowed)
        self.assertFalse(decide_training(rec).allowed)

    def test_missing_approval_denies_public_use(self):
        rec = _fact(
            classification=InformationClass.PUBLIC_COMPANY,
            approval_status=ApprovalStatus.DRAFT,
        )
        self.assertFalse(decide_public(rec).allowed)
        self.assertEqual(decide_public(rec).reason, "deny_not_approved")

    def test_revoked_records_deny_use(self):
        rec = _fact(
            classification=InformationClass.PUBLIC_COMPANY,
            approval_status=ApprovalStatus.APPROVED,
            approved_by=SUBJECT_SAMSON,
            approval_timestamp="2026-01-01T00:00:00Z",
            revocation_status="revoked",
        )
        self.assertFalse(decide_public(rec).allowed)
        self.assertTrue(decide_delete_required(rec).allowed)

    def test_expired_approval_denies_use(self):
        rec = _fact(
            classification=InformationClass.PUBLIC_COMPANY,
            approval_status=ApprovalStatus.APPROVED,
            approved_by=SUBJECT_SAMSON,
            approval_timestamp="2020-01-01T00:00:00Z",
            review_date="2020-06-01",
        )
        self.assertFalse(decide_public(rec, today=date(2026, 8, 5)).allowed)
        self.assertEqual(decide_public(rec, today=date(2026, 8, 5)).reason, "deny_expired")

    def test_secret_cannot_enter_prompts_embed_log_or_training(self):
        rec = _fact(classification=InformationClass.SECRET, approval_status=ApprovalStatus.APPROVED)
        self.assertFalse(decide_model_prompt(rec).allowed)
        self.assertFalse(decide_embed(rec).allowed)
        self.assertFalse(decide_log(rec).allowed)
        self.assertFalse(decide_training(rec).allowed)
        self.assertFalse(decide_public(rec).allowed)

    def test_forget_delete_requires_deletion(self):
        rec = _fact(classification=InformationClass.FORGET_DELETE)
        self.assertFalse(decide_public(rec).allowed)
        self.assertTrue(decide_delete_required(rec).allowed)
        self.assertEqual(decide_delete_required(rec).reason, "require_deletion_workflow")

    def test_owner_private_not_visible_to_guest(self):
        rec = _fact(
            classification=InformationClass.OWNER_PRIVATE,
            subject_id=SUBJECT_SAMSON,
            intended_uses=(AllowedUse.OWNER_ASSISTANCE, AllowedUse.MODEL_PROMPT),
        )
        guest = decide_owner_assistance(
            rec, requester_id="guest", verified_owner=False
        )
        self.assertFalse(guest.allowed)
        owner = decide_owner_assistance(
            rec, requester_id=SUBJECT_SAMSON, verified_owner=True
        )
        self.assertTrue(owner.allowed)

    def test_cofounder_private_cannot_be_approved_by_other_cofounder(self):
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
            can_person_approve(actor_id=SUBJECT_SAMSON, record=james_private)
        )
        self.assertTrue(can_person_approve(actor_id=SUBJECT_JAMES, record=james_private))
        decision = decide_can_approve(james_private, actor_id=SUBJECT_SAMSON)
        self.assertFalse(decision.allowed)

    def test_public_company_approved_may_be_public(self):
        rec = _fact(
            subject="SIONA",
            subject_type=SubjectType.PRODUCT,
            classification=InformationClass.PUBLIC_COMPANY,
            approval_status=ApprovalStatus.APPROVED,
            approved_by=SUBJECT_SAMSON,
            approval_timestamp="2026-08-05T00:00:00Z",
            statement="Unified intelligence engine/platform developed by SIONA Technologies",
        )
        self.assertTrue(decide_public(rec).allowed)

    def test_public_professional_draft_may_not_be_public(self):
        rec = _fact(
            classification=InformationClass.PUBLIC_PROFESSIONAL,
            approval_status=ApprovalStatus.DRAFT,
        )
        self.assertFalse(decide_public(rec).allowed)

    def test_derived_information_inherits_strictest_classification(self):
        derived = inherit_strictest_classification(
            [
                InformationClass.PUBLIC_COMPANY,
                InformationClass.OWNER_PRIVATE,
                InformationClass.SECRET,
            ]
        )
        self.assertEqual(derived, InformationClass.SECRET)
        missing = inherit_strictest_classification(
            [InformationClass.PUBLIC_COMPANY, None]
        )
        self.assertIsNone(missing)

    def test_model_generated_content_cannot_approve_itself(self):
        rec = _fact(
            source_type="model_output",
            approval_status=ApprovalStatus.APPROVED,
            approved_by="model",
            classification=InformationClass.PUBLIC_COMPANY,
        )
        self.assertTrue(model_output_cannot_self_approve(rec))
        self.assertFalse(decide_public(rec).allowed)
        self.assertFalse(decide_can_approve(rec, actor_id=SUBJECT_SAMSON).allowed)

    def test_training_use_denied_by_default(self):
        for cls in InformationClass:
            rec = _fact(
                classification=cls,
                approval_status=ApprovalStatus.APPROVED,
                approved_by=SUBJECT_SAMSON,
                approval_timestamp="2026-01-01T00:00:00Z",
                intended_uses=(AllowedUse.TRAINING_DATASET,),
                prohibited_uses=(),
            )
            self.assertFalse(decide_training(rec).allowed, cls)

    def test_legal_restricted_cannot_enter_ordinary_memory(self):
        rec = _fact(classification=InformationClass.LEGAL_RESTRICTED)
        self.assertFalse(
            decide_owner_assistance(
                rec, requester_id=SUBJECT_SAMSON, verified_owner=True
            ).allowed
        )
        self.assertFalse(decide_model_prompt(rec).allowed)
        self.assertFalse(decide_embed(rec).allowed)
        self.assertFalse(decide_log(rec).allowed)

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
        subjects = {r["subject"] for r in data["records"]}
        self.assertEqual(
            subjects,
            {
                "SIONA Technologies",
                "SIONA",
                "Samson Sibona Njaji",
                "James Ndodana Njaji",
            },
        )
        for rec in data["records"]:
            self.assertEqual(rec["personal_email"], "excluded")
            self.assertEqual(rec["personal_phone"], "excluded")
            self.assertNotIn("email", rec.get("statement", "").lower())
            self.assertNotIn("@", rec.get("statement", ""))
        company = next(r for r in data["records"] if r["subject"] == "SIONA Technologies")
        self.assertEqual(company["approval_status"], "DRAFT")
        product = next(r for r in data["records"] if r["subject"] == "SIONA")
        self.assertEqual(product["approval_status"], "APPROVED")
        self.assertIn("intelligence engine/platform", product["statement"].lower())

    def test_validate_fact_record_rejects_embedded_email_marker(self):
        rec = _fact(personal_email="someone@example.com")
        ok, reason = validate_fact_record(rec)
        self.assertFalse(ok)
        self.assertEqual(reason, "personal_email_must_be_excluded")

    def test_no_ssn_data_dependency(self):
        # Governance must not require writing or reading ssn/data.
        data_dir = ROOT / "ssn" / "data"
        before = sorted(p.name for p in data_dir.iterdir()) if data_dir.is_dir() else []
        _ = decide_public(
            _fact(
                classification=InformationClass.PUBLIC_COMPANY,
                approval_status=ApprovalStatus.APPROVED,
                approved_by=SUBJECT_SAMSON,
                approval_timestamp="2026-08-05T00:00:00Z",
            )
        )
        after = sorted(p.name for p in data_dir.iterdir()) if data_dir.is_dir() else []
        self.assertEqual(before, after)

    def test_revoked_consent_blocks_cofounder_private(self):
        rec = _fact(
            subject_id=SUBJECT_JAMES,
            classification=InformationClass.COFOUNDER_PRIVATE,
            intended_uses=(AllowedUse.OWNER_ASSISTANCE,),
        )
        consent = ConsentRecord(
            subject_id=SUBJECT_JAMES,
            scope="owner_assistance",
            granted=False,
            granted_by=SUBJECT_JAMES,
            timestamp="2026-08-05T00:00:00Z",
            revoked=True,
            revoked_at="2026-08-05T01:00:00Z",
        )
        decision = decide_owner_assistance(
            rec,
            requester_id=SUBJECT_JAMES,
            verified_owner=True,
            consent=consent,
        )
        self.assertFalse(decision.allowed)


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
            path = ROOT / "docs" / name
            self.assertTrue(path.is_file(), name)
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
        self.assertIn("unified intelligence engine/platform", identity.lower())
        self.assertIn("Samson Sibona Njaji", identity)
        self.assertIn("James Ndodana Njaji", identity)
        self.assertIn("Co-founder", identity)
        self.assertIn("personal_email: excluded", public)
        self.assertIn("cannot authorize another co-founder's private information", consent.lower())
        self.assertIn("Secrets are never ordinary memory", private)
        self.assertIn("denied", consent.lower())
        self.assertIn("`TRAINING_DATASET` is **denied**", consent)
        self.assertIn("Audit **sionaglobal.com** only", website)
        self.assertIn("Do **not** modify the website during this task", website)
        self.assertIn("Do **not** automatically treat website content as SIONA memory", website)
        self.assertIn("in progress", status.lower())
        self.assertIn("Phase 4 remains **not started**", status)
        self.assertIn("inactive", status.lower())
        self.assertRegex(adr.replace("\r\n", "\n"), r"(?m)^## Status\n\nProposed\n")
        combined = "\n".join([identity, public, consent, private, website])
        self.assertNotRegex(combined, r"[A-Za-z0-9._%+-]+@gmail\.com", msg="no personal gmail in governance docs")
        self.assertIn("not** an assistant, chatbot", identity.lower())


if __name__ == "__main__":
    unittest.main()
