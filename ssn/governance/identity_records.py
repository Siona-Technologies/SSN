"""Identity fact records and classification inheritance."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence, Tuple

from ssn.governance.information_classes import (
    AllowedUse,
    ApprovalStatus,
    InformationClass,
    SubjectType,
    classification_rank,
)


REQUIRED_FACT_FIELDS = (
    "subject",
    "classification",
    "source_type",
    "source_reference",
    "approval_status",
    "approved_by",
    "approval_timestamp",
    "intended_uses",
    "prohibited_uses",
    "review_date",
    "revocation_status",
)


@dataclass(frozen=True)
class IdentityFactRecord:
    """Bounded identity/fact record. Not runtime memory; not training data."""

    subject: str
    subject_type: SubjectType
    classification: Optional[InformationClass]
    statement: str
    source_type: str
    source_reference: str
    approval_status: ApprovalStatus
    approved_by: str
    approval_timestamp: str
    intended_uses: Tuple[AllowedUse, ...] = ()
    prohibited_uses: Tuple[AllowedUse, ...] = field(
        default_factory=lambda: (AllowedUse.TRAINING_DATASET,)
    )
    review_date: str = ""
    revocation_status: str = "none"  # none | revoked
    subject_id: str = ""
    notes: str = ""
    # Explicit exclusion markers (never store actual private values).
    personal_email: str = "excluded"
    personal_phone: str = "excluded"
    personal_address: str = "excluded"

    def to_dict(self) -> dict:
        return {
            "subject": self.subject,
            "subject_type": self.subject_type.value,
            "classification": None
            if self.classification is None
            else self.classification.value,
            "statement": self.statement,
            "source_type": self.source_type,
            "source_reference": self.source_reference,
            "approval_status": self.approval_status.value,
            "approved_by": self.approved_by,
            "approval_timestamp": self.approval_timestamp,
            "intended_uses": [u.value for u in self.intended_uses],
            "prohibited_uses": [u.value for u in self.prohibited_uses],
            "review_date": self.review_date,
            "revocation_status": self.revocation_status,
            "subject_id": self.subject_id,
            "notes": self.notes,
            "personal_email": self.personal_email,
            "personal_phone": self.personal_phone,
            "personal_address": self.personal_address,
        }


def validate_fact_record(record: IdentityFactRecord) -> Tuple[bool, str]:
    """Structural validation only — does not grant approval or consent."""
    data = record.to_dict()
    for key in REQUIRED_FACT_FIELDS:
        if key not in data:
            return False, f"missing_field:{key}"
        if data[key] is None or data[key] == "":
            if key in {"approved_by", "approval_timestamp", "review_date"} and record.approval_status in {
                ApprovalStatus.DRAFT,
                ApprovalStatus.REJECTED,
            }:
                continue
            if key == "classification":
                return False, "missing_classification"
            return False, f"empty_field:{key}"
    if record.personal_email not in {"excluded", ""}:
        return False, "personal_email_must_be_excluded"
    if record.personal_phone not in {"excluded", ""}:
        return False, "personal_phone_must_be_excluded"
    if record.personal_address not in {"excluded", ""}:
        return False, "personal_address_must_be_excluded"
    return True, "ok"


def inherit_strictest_classification(
    classes: Sequence[Optional[InformationClass]],
) -> Optional[InformationClass]:
    """
    Derived summaries inherit the strongest (strictest) classification of inputs.
    Missing classification is treated as stricter than all known classes (deny-by-default).
    """
    if not classes:
        return None
    if any(c is None for c in classes):
        return None
    return max(classes, key=lambda c: classification_rank(c))  # type: ignore[arg-type]


def model_output_cannot_self_approve(record: IdentityFactRecord) -> bool:
    """Model-generated content cannot grant approval or consent."""
    src = (record.source_type or "").strip().lower()
    if src in {"model_output", "llm", "generated", "self_approved"}:
        return True
    if (record.approved_by or "").strip().lower() in {"model", "llm", "siona", "self"}:
        return True
    return False
