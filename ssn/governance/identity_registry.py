"""
Owner-approved public identity registry (explicit retrieval only).

Loads a fixed local JSON file into immutable IdentityFactRecord tuples.
Does not inject records into LanguageEngine, memory, world model, or providers.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Dict, FrozenSet, Mapping, Optional, Tuple

from ssn.governance.identity_records import (
    IdentityFactRecord,
    MAX_STATEMENT_LEN,
    model_output_cannot_self_approve,
    parse_iso_date,
    validate_fact_record,
)
from ssn.governance.information_classes import (
    AllowedUse,
    ApprovalStatus,
    InformationClass,
    SubjectType,
)

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_REGISTRY_REL = Path("config/governance/approved_identity_records.json")

MAX_REGISTRY_FILE_BYTES = 65536
MAX_REGISTRY_RECORDS = 16
EXPECTED_RECORD_COUNT = 3
MAX_SELECT_SUBJECT_IDS = 16
SUPPORTED_SCHEMA_VERSION = 1
MAX_SUBJECT_ID_LEN = 256
MAX_REGISTRY_READ_BYTES = MAX_REGISTRY_FILE_BYTES + 1

REQUIRED_APPROVED_BY = "person:samson-sibona-njaji"
APPROVED_SOURCE_TYPE = "owner_approval"
APPROVED_SOURCE_REFERENCE = (
    "docs/SIONA_APPROVED_IDENTITY_REGISTRY.md#approval-record-2026-08-06"
)
APPROVED_TIMESTAMP = "2026-08-06T08:20:00Z"
APPROVED_REVIEW_DATE = "2027-08-06"
APPROVED_REVOCATION_STATUS = "none"
APPROVED_EXCLUSION_MARKER = "excluded"
APPROVED_NOTES = ""

_APPROVED_INTENDED_USES: Tuple[AllowedUse, ...] = (
    AllowedUse.PUBLIC_RESPONSE,
    AllowedUse.MODEL_PROMPT,
    AllowedUse.RETRIEVAL,
)
_APPROVED_PROHIBITED_USES: Tuple[AllowedUse, ...] = (AllowedUse.TRAINING_DATASET,)
_APPROVED_INTENDED_SET: FrozenSet[AllowedUse] = frozenset(_APPROVED_INTENDED_USES)
_APPROVED_PROHIBITED_SET: FrozenSet[AllowedUse] = frozenset(_APPROVED_PROHIBITED_USES)

REQUIRED_SUBJECT_IDS: FrozenSet[str] = frozenset(
    {
        "company:siona-technologies",
        "product:siona",
        "person:samson-sibona-njaji",
    }
)


@dataclass(frozen=True)
class _ApprovedManifestEntry:
    subject: str
    subject_id: str
    subject_type: SubjectType
    classification: InformationClass
    statement: str
    source_type: str
    source_reference: str
    approval_status: ApprovalStatus
    approved_by: str
    approval_timestamp: str
    intended_uses: Tuple[AllowedUse, ...]
    prohibited_uses: Tuple[AllowedUse, ...]
    review_date: str
    revocation_status: str
    personal_email: str
    personal_phone: str
    personal_address: str
    notes: str


_APPROVED_MANIFEST: Dict[str, _ApprovedManifestEntry] = {
    "company:siona-technologies": _ApprovedManifestEntry(
        subject="SIONA Technologies",
        subject_id="company:siona-technologies",
        subject_type=SubjectType.COMPANY,
        classification=InformationClass.PUBLIC_COMPANY,
        statement=(
            "SIONA Technologies is an African-founded technology company developing "
            "software, intelligent systems and digital infrastructure."
        ),
        source_type=APPROVED_SOURCE_TYPE,
        source_reference=APPROVED_SOURCE_REFERENCE,
        approval_status=ApprovalStatus.APPROVED,
        approved_by=REQUIRED_APPROVED_BY,
        approval_timestamp=APPROVED_TIMESTAMP,
        intended_uses=_APPROVED_INTENDED_USES,
        prohibited_uses=_APPROVED_PROHIBITED_USES,
        review_date=APPROVED_REVIEW_DATE,
        revocation_status=APPROVED_REVOCATION_STATUS,
        personal_email=APPROVED_EXCLUSION_MARKER,
        personal_phone=APPROVED_EXCLUSION_MARKER,
        personal_address=APPROVED_EXCLUSION_MARKER,
        notes=APPROVED_NOTES,
    ),
    "product:siona": _ApprovedManifestEntry(
        subject="SIONA",
        subject_id="product:siona",
        subject_type=SubjectType.PRODUCT,
        classification=InformationClass.PUBLIC_COMPANY,
        statement=(
            "SIONA is the unified intelligence engine and platform developed by "
            "SIONA Technologies."
        ),
        source_type=APPROVED_SOURCE_TYPE,
        source_reference=APPROVED_SOURCE_REFERENCE,
        approval_status=ApprovalStatus.APPROVED,
        approved_by=REQUIRED_APPROVED_BY,
        approval_timestamp=APPROVED_TIMESTAMP,
        intended_uses=_APPROVED_INTENDED_USES,
        prohibited_uses=_APPROVED_PROHIBITED_USES,
        review_date=APPROVED_REVIEW_DATE,
        revocation_status=APPROVED_REVOCATION_STATUS,
        personal_email=APPROVED_EXCLUSION_MARKER,
        personal_phone=APPROVED_EXCLUSION_MARKER,
        personal_address=APPROVED_EXCLUSION_MARKER,
        notes=APPROVED_NOTES,
    ),
    "person:samson-sibona-njaji": _ApprovedManifestEntry(
        subject="Samson Sibona Njaji",
        subject_id="person:samson-sibona-njaji",
        subject_type=SubjectType.PERSON,
        classification=InformationClass.PUBLIC_PROFESSIONAL,
        statement=(
            "Samson Sibona Njaji is a Kenyan software engineer and technology "
            "entrepreneur, a co-founder of SIONA Technologies, and is involved in the "
            "design and development of SIONA."
        ),
        source_type=APPROVED_SOURCE_TYPE,
        source_reference=APPROVED_SOURCE_REFERENCE,
        approval_status=ApprovalStatus.APPROVED,
        approved_by=REQUIRED_APPROVED_BY,
        approval_timestamp=APPROVED_TIMESTAMP,
        intended_uses=_APPROVED_INTENDED_USES,
        prohibited_uses=_APPROVED_PROHIBITED_USES,
        review_date=APPROVED_REVIEW_DATE,
        revocation_status=APPROVED_REVOCATION_STATUS,
        personal_email=APPROVED_EXCLUSION_MARKER,
        personal_phone=APPROVED_EXCLUSION_MARKER,
        personal_address=APPROVED_EXCLUSION_MARKER,
        notes=APPROVED_NOTES,
    ),
}

PUBLIC_CLASSIFICATIONS: FrozenSet[InformationClass] = frozenset(
    {InformationClass.PUBLIC_COMPANY, InformationClass.PUBLIC_PROFESSIONAL}
)
REQUIRED_INTENDED_USES: FrozenSet[AllowedUse] = _APPROVED_INTENDED_SET

_RECORD_FIELDS = frozenset(
    {
        "subject",
        "subject_id",
        "subject_type",
        "classification",
        "statement",
        "source_type",
        "source_reference",
        "approval_status",
        "approved_by",
        "approval_timestamp",
        "intended_uses",
        "prohibited_uses",
        "review_date",
        "revocation_status",
        "personal_email",
        "personal_phone",
        "personal_address",
        "notes",
    }
)


class ApprovedIdentityRegistryError(ValueError):
    """Raised when registry load or selection violates strict bounds."""


@dataclass(frozen=True)
class ApprovedIdentityRegistry:
    """Immutable approved identity registry."""

    records: Tuple[IdentityFactRecord, ...]
    schema_version: int

    def all_records(self) -> Tuple[IdentityFactRecord, ...]:
        return self.records

    def get_by_subject_id(self, subject_id: str) -> Optional[IdentityFactRecord]:
        if type(subject_id) is not str or not subject_id:
            return None
        for record in self.records:
            if record.subject_id == subject_id:
                return record
        return None

    def select_by_subject_ids(
        self, subject_ids: Tuple[str, ...] | list[str]
    ) -> Tuple[IdentityFactRecord, ...]:
        if type(subject_ids) is not tuple and type(subject_ids) is not list:
            raise ApprovedIdentityRegistryError("invalid_subject_ids")
        candidate_count = len(subject_ids)
        if candidate_count > MAX_SELECT_SUBJECT_IDS:
            raise ApprovedIdentityRegistryError("deny_subject_id_limit")
        seen: set[str] = set()
        selected: list[IdentityFactRecord] = []
        for index in range(candidate_count):
            raw_id = subject_ids[index]
            if type(raw_id) is not str:
                raise ApprovedIdentityRegistryError("invalid_subject_ids")
            if not raw_id or raw_id in seen:
                continue
            seen.add(raw_id)
            record = self.get_by_subject_id(raw_id)
            if record is not None:
                selected.append(record)
        selected.sort(key=lambda r: r.subject_id)
        return tuple(selected)

    def public_response_records(
        self, subject_ids: Optional[Tuple[str, ...] | list[str]] = None
    ) -> Tuple[IdentityFactRecord, ...]:
        if subject_ids is None:
            return self.records
        return self.select_by_subject_ids(subject_ids)


def get_default_approved_identity_registry_path() -> Path:
    """Repository-relative default path for the approved identity registry."""
    return _REPO_ROOT / _DEFAULT_REGISTRY_REL


def _read_registry_file_bytes(path: Path) -> bytes:
    """Read registry bytes with stat-first and bounded read enforcement."""
    try:
        stat_result = os.stat(path)
    except OSError:
        raise ApprovedIdentityRegistryError("registry_file_not_found")
    if stat_result.st_size > MAX_REGISTRY_FILE_BYTES:
        raise ApprovedIdentityRegistryError("registry_file_too_large")
    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_REGISTRY_READ_BYTES)
    except OSError:
        raise ApprovedIdentityRegistryError("registry_file_not_found")
    if len(data) > MAX_REGISTRY_FILE_BYTES:
        raise ApprovedIdentityRegistryError("registry_file_too_large")
    return data


def load_approved_identity_registry(
    path: Optional[Path | str] = None,
    *,
    today: Optional[date] = None,
) -> ApprovedIdentityRegistry:
    """
    Load and validate the approved identity registry from a local JSON file.

    Fails atomically on any validation error. No partial load.
    """
    registry_path = (
        Path(path) if path is not None else get_default_approved_identity_registry_path()
    )
    registry_path = registry_path.resolve()
    if not registry_path.is_file():
        raise ApprovedIdentityRegistryError("registry_file_not_found")

    raw_bytes = _read_registry_file_bytes(registry_path)

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise ApprovedIdentityRegistryError("registry_invalid_utf8")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        raise ApprovedIdentityRegistryError("registry_invalid_json")

    if not isinstance(payload, dict):
        raise ApprovedIdentityRegistryError("registry_invalid_root")

    unknown_top = set(payload.keys()) - {"schema_version", "records"}
    if unknown_top:
        raise ApprovedIdentityRegistryError("registry_unknown_top_level")

    schema_version = payload.get("schema_version")
    if schema_version is None:
        raise ApprovedIdentityRegistryError("registry_missing_schema_version")
    if type(schema_version) is bool or type(schema_version) is not int:
        raise ApprovedIdentityRegistryError("registry_invalid_schema_version")
    if schema_version != SUPPORTED_SCHEMA_VERSION:
        raise ApprovedIdentityRegistryError("registry_unsupported_schema_version")

    records_raw = payload.get("records")
    if not isinstance(records_raw, list):
        raise ApprovedIdentityRegistryError("registry_records_not_list")
    if len(records_raw) > MAX_REGISTRY_RECORDS:
        raise ApprovedIdentityRegistryError("registry_too_many_records")
    if len(records_raw) != EXPECTED_RECORD_COUNT:
        raise ApprovedIdentityRegistryError("registry_record_count_mismatch")

    today_value = today or date.today()
    parsed: list[IdentityFactRecord] = []
    for index, item in enumerate(records_raw):
        if not isinstance(item, dict):
            raise ApprovedIdentityRegistryError(f"registry_record_not_object:{index}")
        record = _parse_record_object(item, index=index)
        _validate_registry_record(record, today=today_value)
        _validate_approved_manifest(record)
        parsed.append(record)

    subject_ids: list[str] = []
    statements: list[str] = []
    for record in parsed:
        if record.subject_id in subject_ids:
            raise ApprovedIdentityRegistryError("registry_duplicate_subject_id")
        if record.statement in statements:
            raise ApprovedIdentityRegistryError("registry_duplicate_statement")
        subject_ids.append(record.subject_id)
        statements.append(record.statement)

    found_ids = frozenset(subject_ids)
    if found_ids != frozenset(_APPROVED_MANIFEST.keys()):
        raise ApprovedIdentityRegistryError("registry_approved_manifest_mismatch")

    parsed.sort(key=lambda r: r.subject_id)
    return ApprovedIdentityRegistry(
        records=tuple(parsed),
        schema_version=schema_version,
    )


def _parse_record_object(item: Mapping[str, Any], *, index: int) -> IdentityFactRecord:
    unknown = set(item.keys()) - _RECORD_FIELDS
    if unknown:
        raise ApprovedIdentityRegistryError(
            f"registry_record_unknown_field:{index}"
        )

    required_fields = _RECORD_FIELDS - {"notes"}
    for field in required_fields:
        if field not in item:
            raise ApprovedIdentityRegistryError(
                f"registry_record_missing_field:{index}:{field}"
            )

    subject = _require_str(item.get("subject"), f"registry_record_invalid_subject:{index}")
    subject_id = _require_str(
        item.get("subject_id"), f"registry_record_invalid_subject_id:{index}"
    )
    if len(subject_id) > MAX_SUBJECT_ID_LEN:
        raise ApprovedIdentityRegistryError(
            f"registry_record_invalid_subject_id:{index}"
        )

    subject_type = _parse_enum(
        item.get("subject_type"), SubjectType, f"registry_record_invalid_subject_type:{index}"
    )
    classification = _parse_enum(
        item.get("classification"),
        InformationClass,
        f"registry_record_invalid_classification:{index}",
    )
    statement = _require_str(
        item.get("statement"), f"registry_record_invalid_statement:{index}"
    )
    if len(statement) > MAX_STATEMENT_LEN:
        raise ApprovedIdentityRegistryError(
            f"registry_record_invalid_statement:{index}"
        )

    source_type = _require_str(
        item.get("source_type"), f"registry_record_invalid_source_type:{index}"
    )
    source_reference = _require_str(
        item.get("source_reference"),
        f"registry_record_invalid_source_reference:{index}",
    )
    approval_status = _parse_enum(
        item.get("approval_status"),
        ApprovalStatus,
        f"registry_record_invalid_approval_status:{index}",
    )
    approved_by = _require_str(
        item.get("approved_by"), f"registry_record_invalid_approved_by:{index}"
    )
    approval_timestamp = _require_str(
        item.get("approval_timestamp"),
        f"registry_record_invalid_approval_timestamp:{index}",
    )
    intended_uses = _parse_use_tuple(
        item.get("intended_uses"),
        f"registry_record_invalid_intended_uses:{index}",
    )
    prohibited_uses = _parse_use_tuple(
        item.get("prohibited_uses"),
        f"registry_record_invalid_prohibited_uses:{index}",
    )
    review_date = _require_str(
        item.get("review_date"), f"registry_record_invalid_review_date:{index}"
    )
    revocation_status = _require_str(
        item.get("revocation_status"),
        f"registry_record_invalid_revocation_status:{index}",
    )
    personal_email = _require_str(
        item.get("personal_email"),
        f"registry_record_invalid_personal_email:{index}",
    )
    personal_phone = _require_str(
        item.get("personal_phone"),
        f"registry_record_invalid_personal_phone:{index}",
    )
    personal_address = _require_str(
        item.get("personal_address"),
        f"registry_record_invalid_personal_address:{index}",
    )
    notes_raw = item.get("notes", "")
    if notes_raw is None:
        notes_raw = ""
    if type(notes_raw) is not str:
        raise ApprovedIdentityRegistryError(f"registry_record_invalid_notes:{index}")

    return IdentityFactRecord(
        subject=subject,
        subject_type=subject_type,
        classification=classification,
        statement=statement,
        source_type=source_type,
        source_reference=source_reference,
        approval_status=approval_status,
        approved_by=approved_by,
        approval_timestamp=approval_timestamp,
        intended_uses=intended_uses,
        prohibited_uses=prohibited_uses,
        review_date=review_date,
        revocation_status=revocation_status,
        subject_id=subject_id,
        notes=notes_raw,
        personal_email=personal_email,
        personal_phone=personal_phone,
        personal_address=personal_address,
    )


def _require_str(value: Any, code: str) -> str:
    if type(value) is not str:
        raise ApprovedIdentityRegistryError(code)
    return value


def _parse_enum(value: Any, enum_cls: type, code: str) -> Any:
    if type(value) is not str:
        raise ApprovedIdentityRegistryError(code)
    try:
        return enum_cls(value)
    except ValueError:
        raise ApprovedIdentityRegistryError(code)


def _parse_use_tuple(value: Any, code: str) -> Tuple[AllowedUse, ...]:
    if not isinstance(value, list):
        raise ApprovedIdentityRegistryError(code)
    uses: list[AllowedUse] = []
    for item in value:
        if type(item) is not str:
            raise ApprovedIdentityRegistryError(code)
        try:
            uses.append(AllowedUse(item))
        except ValueError:
            raise ApprovedIdentityRegistryError(code)
    return tuple(uses)


def _validate_approved_manifest(record: IdentityFactRecord) -> None:
    entry = _APPROVED_MANIFEST.get(record.subject_id)
    if entry is None:
        raise ApprovedIdentityRegistryError("registry_approved_manifest_mismatch")

    if record.statement != entry.statement:
        raise ApprovedIdentityRegistryError("registry_approved_statement_mismatch")

    metadata_pairs = (
        ("subject", record.subject),
        ("subject_id", record.subject_id),
        ("subject_type", record.subject_type),
        ("classification", record.classification),
        ("source_type", record.source_type),
        ("source_reference", record.source_reference),
        ("approval_status", record.approval_status),
        ("approved_by", record.approved_by),
        ("approval_timestamp", record.approval_timestamp),
        ("review_date", record.review_date),
        ("revocation_status", record.revocation_status),
        ("personal_email", record.personal_email),
        ("personal_phone", record.personal_phone),
        ("personal_address", record.personal_address),
        ("notes", record.notes),
    )
    for field_name, actual in metadata_pairs:
        expected = getattr(entry, field_name)
        if actual != expected:
            raise ApprovedIdentityRegistryError("registry_approved_metadata_mismatch")

    intended_set = frozenset(record.intended_uses)
    if (
        intended_set != _APPROVED_INTENDED_SET
        or len(record.intended_uses) != len(_APPROVED_INTENDED_USES)
    ):
        raise ApprovedIdentityRegistryError("registry_intended_uses_mismatch")

    prohibited_set = frozenset(record.prohibited_uses)
    if (
        prohibited_set != _APPROVED_PROHIBITED_SET
        or len(record.prohibited_uses) != len(_APPROVED_PROHIBITED_USES)
    ):
        raise ApprovedIdentityRegistryError("registry_prohibited_uses_mismatch")


def _validate_registry_record(record: IdentityFactRecord, *, today: date) -> None:
    ok, reason = validate_fact_record(record)
    if not ok:
        raise ApprovedIdentityRegistryError(f"registry_record_invalid:{reason}")

    if record.approval_status is not ApprovalStatus.APPROVED:
        raise ApprovedIdentityRegistryError("registry_record_not_approved")

    if (record.revocation_status or "").strip().lower() == "revoked":
        raise ApprovedIdentityRegistryError("registry_record_revoked")

    review, _ = parse_iso_date(record.review_date)
    if review is None:
        raise ApprovedIdentityRegistryError("registry_record_invalid_review_date")
    if review < today:
        raise ApprovedIdentityRegistryError("registry_record_expired")

    if model_output_cannot_self_approve(record):
        raise ApprovedIdentityRegistryError("registry_record_model_self_approve")
