"""Identity fact records, validation, and classification inheritance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
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

_ALLOWED_REVOCATION = frozenset({"none", "revoked"})

MAX_SUBJECT_LEN = 256
MAX_STATEMENT_LEN = 4000
MAX_SOURCE_LEN = 512
MAX_NOTES_LEN = 1000


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


def is_valid_iso_instant(value: str) -> Tuple[bool, str]:
    """
    Full ISO date/timestamp validation via stdlib parsing (no third-party deps).

    Accepts YYYY-MM-DD, or datetime with optional fractional seconds and
    Z / ±HH:MM offset. Rejects impossible calendar dates, clock times, and offsets.
    """
    text = (value or "").strip()
    if not text:
        return False, "empty_timestamp"

    # Date-only form.
    if "T" not in text and " " not in text:
        try:
            date.fromisoformat(text)
            return True, "ok"
        except ValueError:
            return False, "invalid_timestamp_value"

    # Datetime: normalize space separator and trailing Z.
    normalized = text.replace(" ", "T", 1)
    if normalized.endswith("Z") or normalized.endswith("z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        datetime.fromisoformat(normalized)
    except ValueError:
        return False, "invalid_timestamp_value"
    return True, "ok"


def parse_iso_date(value: str) -> Tuple[Optional[date], str]:
    """Parse a governance date/timestamp; return calendar date or failure."""
    text = (value or "").strip()
    if not text:
        return None, "empty_date"
    ok, reason = is_valid_iso_instant(text)
    if not ok:
        if reason == "empty_timestamp":
            return None, "empty_date"
        return None, "invalid_date_value"
    try:
        return date.fromisoformat(text[:10]), "ok"
    except ValueError:
        return None, "invalid_date_value"


def parse_iso_timestamp(value: str) -> Tuple[bool, str]:
    ok, _reason = is_valid_iso_instant(value)
    if not ok:
        return False, "invalid_approval_timestamp"
    return True, "ok"


def validate_fact_record(record: IdentityFactRecord) -> Tuple[bool, str]:
    """Structural validation only — does not grant approval or consent."""
    if record.classification is None:
        return False, "missing_classification"

    subject = (record.subject or "").strip()
    statement = (record.statement or "").strip()
    source_type = (record.source_type or "").strip()
    source_reference = (record.source_reference or "").strip()
    if not subject or not statement or not source_type or not source_reference:
        return False, "deny_invalid_record"
    if len(subject) > MAX_SUBJECT_LEN or len(statement) > MAX_STATEMENT_LEN:
        return False, "deny_invalid_record"
    if len(source_type) > MAX_SOURCE_LEN or len(source_reference) > MAX_SOURCE_LEN:
        return False, "deny_invalid_record"
    if len(record.notes or "") > MAX_NOTES_LEN:
        return False, "deny_invalid_record"

    rev = (record.revocation_status or "").strip().lower()
    if rev not in _ALLOWED_REVOCATION:
        return False, "invalid_revocation_status"

    if not isinstance(record.intended_uses, tuple) or not isinstance(
        record.prohibited_uses, tuple
    ):
        return False, "deny_invalid_record"
    for use in list(record.intended_uses) + list(record.prohibited_uses):
        if not isinstance(use, AllowedUse):
            return False, "deny_invalid_record"

    if record.personal_email not in {"excluded", ""}:
        return False, "personal_email_must_be_excluded"
    if record.personal_phone not in {"excluded", ""}:
        return False, "personal_phone_must_be_excluded"
    if record.personal_address not in {"excluded", ""}:
        return False, "personal_address_must_be_excluded"

    if record.approval_status == ApprovalStatus.APPROVED:
        if not (record.approved_by or "").strip():
            return False, "deny_invalid_record"
        ok_ts, ts_reason = parse_iso_timestamp(record.approval_timestamp)
        if not ok_ts:
            return False, "invalid_approval_timestamp"
        review, rev_reason = parse_iso_date(record.review_date)
        if review is None:
            return False, "invalid_review_date"

    if record.approval_status in {ApprovalStatus.DRAFT, ApprovalStatus.REJECTED}:
        # Draft/rejected may omit approval fields.
        if record.review_date.strip():
            review, rev_reason = parse_iso_date(record.review_date)
            if review is None:
                return False, "invalid_review_date"
        if record.approval_timestamp.strip():
            ok_ts, ts_reason = parse_iso_timestamp(record.approval_timestamp)
            if not ok_ts:
                return False, "invalid_approval_timestamp"

    return True, "ok"


def inherit_strictest_classification(
    classes: Sequence[Optional[InformationClass]],
) -> Optional[InformationClass]:
    """
    Derived summaries inherit the strongest (strictest) classification of inputs.
    Missing classification is treated as fail-closed (None).
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
    if (record.approved_by or "").strip().lower() in {
        "model",
        "llm",
        "siona",
        "self",
        "system",
    }:
        return True
    return False
