"""Tests for owner-approved identity registry (EXP-3B-007).

Synthetic approved public facts only. No network, llama.cpp, model load,
ssn/data mutation, or real personal contact data.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List
from unittest import mock

from ssn.core.language_engine import LanguageEngine
from ssn.core.llm_providers import LocalDummyLLMProvider
from ssn.governance.identity_registry import (
    ApprovedIdentityRegistry,
    ApprovedIdentityRegistryError,
    EXPECTED_RECORD_COUNT,
    MAX_REGISTRY_FILE_BYTES,
    MAX_REGISTRY_READ_BYTES,
    MAX_SELECT_SUBJECT_IDS,
    REQUIRED_APPROVED_BY,
    REQUIRED_SUBJECT_IDS,
    SUPPORTED_SCHEMA_VERSION,
    _read_registry_file_bytes,
    get_default_approved_identity_registry_path,
    load_approved_identity_registry,
)
from ssn.governance.information_classes import AllowedUse
from ssn.governance.policy import (
    PolicyContext,
    decide_model_prompt,
    decide_public,
    decide_training,
)
from ssn.governance.runtime_context import (
    ContextAudience,
    GovernedContextAssembler,
    GovernedContextInput,
)

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "ssn" / "data"
WORLD_MODEL = DATA_DIR / "world_model.json"
DEFAULT_PATH = get_default_approved_identity_registry_path()

SENSITIVE_PATTERNS = [
    re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", re.I),
    re.compile(r"\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    re.compile(r"-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----"),
]

STMT_COMPANY = (
    "SIONA Technologies is an African-founded technology company developing "
    "software, intelligent systems and digital infrastructure."
)
STMT_PRODUCT = (
    "SIONA is the unified intelligence engine and platform developed by "
    "SIONA Technologies."
)
STMT_PERSON = (
    "Samson Sibona Njaji is a Kenyan software engineer and technology "
    "entrepreneur, a co-founder of SIONA Technologies, and is involved in the "
    "design and development of SIONA."
)
APPROVED_STATEMENTS = (STMT_COMPANY, STMT_PRODUCT, STMT_PERSON)

ENV_GOVERNED = "SSN_GOVERNED_CONTEXT"


def _guest_ctx() -> PolicyContext:
    return PolicyContext(
        actor_id="guest:anon",
        actor_authenticated=False,
        verified_owner=False,
        authorized_company_approver_ids=(),
    )


def _default_registry_dict() -> Dict[str, Any]:
    return json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))


def _write_registry(directory: Path, payload: Dict[str, Any]) -> Path:
    path = directory / "registry.json"
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    return path


def _mutate_record(
    directory: Path, subject_id: str, **changes: Any
) -> Path:
    payload = _default_registry_dict()
    for record in payload["records"]:
        if record["subject_id"] == subject_id:
            record.update(changes)
    return _write_registry(directory, payload)


class TestApprovedManifestIntegrity(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._tmp = Path(self._tmpdir.name)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def test_changed_company_statement_fails(self) -> None:
        path = _mutate_record(
            self._tmp,
            "company:siona-technologies",
            statement="Tampered company statement.",
        )
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_approved_statement_mismatch")

    def test_changed_siona_statement_fails(self) -> None:
        path = _mutate_record(self._tmp, "product:siona", statement="Tampered SIONA.")
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_approved_statement_mismatch")

    def test_changed_samson_statement_fails(self) -> None:
        path = _mutate_record(
            self._tmp,
            "person:samson-sibona-njaji",
            statement="Tampered Samson statement.",
        )
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_approved_statement_mismatch")

    def test_changed_subject_name_fails(self) -> None:
        path = _mutate_record(self._tmp, "product:siona", subject="SIONA Tampered")
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_approved_metadata_mismatch")

    def test_changed_subject_type_fails(self) -> None:
        path = _mutate_record(self._tmp, "product:siona", subject_type="COMPANY")
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_approved_metadata_mismatch")

    def test_changed_classification_fails(self) -> None:
        path = _mutate_record(
            self._tmp,
            "person:samson-sibona-njaji",
            classification="PUBLIC_COMPANY",
        )
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_approved_metadata_mismatch")

    def test_changed_source_type_fails(self) -> None:
        path = _mutate_record(self._tmp, "product:siona", source_type="website")
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_approved_metadata_mismatch")

    def test_changed_source_reference_fails(self) -> None:
        path = _mutate_record(self._tmp, "product:siona", source_reference="docs/other")
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_approved_metadata_mismatch")

    def test_changed_approval_timestamp_fails(self) -> None:
        path = _mutate_record(
            self._tmp, "product:siona", approval_timestamp="2026-08-07T00:00:00Z"
        )
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_approved_metadata_mismatch")

    def test_changed_review_date_fails(self) -> None:
        path = _mutate_record(self._tmp, "product:siona", review_date="2028-01-01")
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_approved_metadata_mismatch")

    def test_changed_revocation_status_fails(self) -> None:
        path = _mutate_record(self._tmp, "product:siona", revocation_status="revoked")
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_record_revoked")

    def test_additional_intended_use_fails(self) -> None:
        path = _mutate_record(
            self._tmp,
            "product:siona",
            intended_uses=[
                "PUBLIC_RESPONSE",
                "MODEL_PROMPT",
                "RETRIEVAL",
                "PUBLIC_WEBSITE",
            ],
        )
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_intended_uses_mismatch")

    def test_duplicate_intended_use_fails(self) -> None:
        path = _mutate_record(
            self._tmp,
            "product:siona",
            intended_uses=["PUBLIC_RESPONSE", "PUBLIC_RESPONSE", "MODEL_PROMPT", "RETRIEVAL"],
        )
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_intended_uses_mismatch")

    def test_reordered_intended_uses_pass_exact_set(self) -> None:
        payload = _default_registry_dict()
        payload["records"][1]["intended_uses"] = [
            "RETRIEVAL",
            "MODEL_PROMPT",
            "PUBLIC_RESPONSE",
        ]
        path = _write_registry(self._tmp, payload)
        registry = load_approved_identity_registry(path)
        self.assertEqual(len(registry.all_records()), 3)

    def test_additional_prohibited_use_fails(self) -> None:
        path = _mutate_record(
            self._tmp,
            "product:siona",
            prohibited_uses=["TRAINING_DATASET", "PUBLIC_WEBSITE"],
        )
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_prohibited_uses_mismatch")

    def test_duplicate_prohibited_use_fails(self) -> None:
        path = _mutate_record(
            self._tmp,
            "product:siona",
            prohibited_uses=["TRAINING_DATASET", "TRAINING_DATASET"],
        )
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_prohibited_uses_mismatch")

    def test_unapproved_notes_fail(self) -> None:
        path = _mutate_record(self._tmp, "product:siona", notes="unapproved note")
        with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
            load_approved_identity_registry(path)
        self.assertEqual(str(ctx.exception), "registry_approved_metadata_mismatch")

    def test_stat_limit_rejects_before_open(self) -> None:
        path = (self._tmp / "registry.json").resolve()
        path.write_bytes(b"{}")
        with mock.patch(
            "ssn.governance.identity_registry.os.stat",
            return_value=SimpleNamespace(st_size=MAX_REGISTRY_FILE_BYTES + 1),
        ):
            with mock.patch("io.open") as mock_open:
                with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
                    _read_registry_file_bytes(path)
                self.assertEqual(str(ctx.exception), "registry_file_too_large")
                mock_open.assert_not_called()

    def test_bounded_read_max_bytes(self) -> None:
        path = (self._tmp / "small.json").resolve()
        path.write_bytes(b"{}")
        read_sizes: list[int] = []

        class _TrackingReader:
            def __init__(self, data: bytes) -> None:
                self._data = data

            def read(self, size: int = -1) -> bytes:
                if size < 0:
                    chunk = self._data
                else:
                    chunk = self._data[:size]
                    self._data = self._data[len(chunk):]
                read_sizes.append(len(chunk))
                return chunk

            def __enter__(self) -> "_TrackingReader":
                return self

            def __exit__(self, *args: object) -> None:
                return None

        with mock.patch(
            "ssn.governance.identity_registry.os.stat",
            return_value=SimpleNamespace(st_size=2),
        ):
            with mock.patch("io.open", return_value=_TrackingReader(b"{}")):
                data = _read_registry_file_bytes(path)
        self.assertEqual(data, b"{}")
        self.assertLessEqual(sum(read_sizes), MAX_REGISTRY_READ_BYTES)

    def test_post_stat_growth_rejected(self) -> None:
        path = (self._tmp / "registry.json").resolve()
        path.write_bytes(b"x")
        with mock.patch(
            "ssn.governance.identity_registry.os.stat",
            return_value=SimpleNamespace(st_size=1),
        ):
            with mock.patch(
                "io.open",
                mock.mock_open(read_data=b"x" * (MAX_REGISTRY_FILE_BYTES + 1)),
            ):
                with self.assertRaises(ApprovedIdentityRegistryError) as ctx:
                    _read_registry_file_bytes(path)
                self.assertEqual(str(ctx.exception), "registry_file_too_large")

    def test_selection_list_subclass_rejected(self) -> None:
        registry = load_approved_identity_registry()

        class _SubList(list):
            pass

        with self.assertRaises(ApprovedIdentityRegistryError):
            registry.select_by_subject_ids(_SubList(["product:siona"]))

    def test_selection_generator_rejected(self) -> None:
        registry = load_approved_identity_registry()
        with self.assertRaises(ApprovedIdentityRegistryError):
            registry.select_by_subject_ids(iter(["product:siona"]))

    def test_selection_malformed_id_rejected(self) -> None:
        registry = load_approved_identity_registry()
        with self.assertRaises(ApprovedIdentityRegistryError):
            registry.select_by_subject_ids(["product:siona", 42])

    def test_selection_exact_casing_required(self) -> None:
        registry = load_approved_identity_registry()
        self.assertIsNone(registry.get_by_subject_id("Product:siona"))
        selected = registry.select_by_subject_ids(["Product:siona"])
        self.assertEqual(len(selected), 0)


class TestApprovedIdentityRegistry(unittest.TestCase):
    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self._tmp = Path(self._tmpdir.name)
        self._world_mtime = (
            WORLD_MODEL.stat().st_mtime_ns if WORLD_MODEL.exists() else None
        )
        self._data_listing = (
            tuple(sorted(p.name for p in DATA_DIR.iterdir()))
            if DATA_DIR.is_dir()
            else ()
        )

    def tearDown(self) -> None:
        self._tmpdir.cleanup()
        if WORLD_MODEL.exists() and self._world_mtime is not None:
            self.assertEqual(WORLD_MODEL.stat().st_mtime_ns, self._world_mtime)
        if DATA_DIR.is_dir():
            self.assertEqual(
                tuple(sorted(p.name for p in DATA_DIR.iterdir())),
                self._data_listing,
            )

    def test_01_default_registry_loads(self) -> None:
        registry = load_approved_identity_registry()
        self.assertIsInstance(registry, ApprovedIdentityRegistry)

    def test_02_exactly_three_records(self) -> None:
        registry = load_approved_identity_registry()
        self.assertEqual(len(registry.all_records()), EXPECTED_RECORD_COUNT)

    def test_03_exact_subject_ids(self) -> None:
        registry = load_approved_identity_registry()
        ids = {r.subject_id for r in registry.all_records()}
        self.assertEqual(ids, set(REQUIRED_SUBJECT_IDS))

    def test_04_exact_statements(self) -> None:
        registry = load_approved_identity_registry()
        statements = {r.statement for r in registry.all_records()}
        self.assertEqual(statements, set(APPROVED_STATEMENTS))

    def test_05_deterministic_ordering(self) -> None:
        r1 = load_approved_identity_registry()
        r2 = load_approved_identity_registry()
        self.assertEqual(
            [rec.subject_id for rec in r1.all_records()],
            [rec.subject_id for rec in r2.all_records()],
        )
        self.assertEqual(
            r1.all_records()[0].subject_id,
            "company:siona-technologies",
        )

    def test_06_records_immutable(self) -> None:
        registry = load_approved_identity_registry()
        records = registry.all_records()
        self.assertIsInstance(records, tuple)
        self.assertIs(records, registry.records)
        self.assertEqual(len(records), EXPECTED_RECORD_COUNT)

    def test_07_duplicate_subject_ids_fail(self) -> None:
        payload = _default_registry_dict()
        dup = dict(payload["records"][0])
        dup["subject_id"] = payload["records"][1]["subject_id"]
        payload["records"] = [payload["records"][0], dup, payload["records"][2]]
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_08_duplicate_statements_fail(self) -> None:
        payload = _default_registry_dict()
        dup = dict(payload["records"][1])
        dup["statement"] = payload["records"][0]["statement"]
        payload["records"] = [payload["records"][0], dup, payload["records"][2]]
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_09_unknown_schema_version_fails(self) -> None:
        payload = _default_registry_dict()
        payload["schema_version"] = 99
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_10_missing_schema_version_fails(self) -> None:
        payload = _default_registry_dict()
        del payload["schema_version"]
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_11_oversized_file_fails_before_parse(self) -> None:
        path = self._tmp / "big.json"
        path.write_bytes(b" " * (MAX_REGISTRY_FILE_BYTES + 1))
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_12_invalid_utf8_fails(self) -> None:
        path = self._tmp / "badutf8.json"
        path.write_bytes(b'{"schema_version": 1, "records": [\xff]}')
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_13_non_object_root_fails(self) -> None:
        path = self._tmp / "root.json"
        path.write_text(json.dumps([1, 2]), encoding="utf-8")
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_14_non_list_records_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"] = {}
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_15_missing_required_field_fails(self) -> None:
        payload = _default_registry_dict()
        del payload["records"][0]["statement"]
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_16_invalid_enum_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"][0]["subject_type"] = "INVALID_TYPE"
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_17_draft_record_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"][0]["approval_status"] = "DRAFT"
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_18_rejected_record_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"][0]["approval_status"] = "REJECTED"
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_19_revoked_record_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"][0]["revocation_status"] = "revoked"
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_20_expired_record_fails(self) -> None:
        payload = _default_registry_dict()
        for rec in payload["records"]:
            rec["review_date"] = "2020-01-01"
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path, today=date(2026, 8, 6))

    def test_21_non_public_classification_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"][0]["classification"] = "SECRET"
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_22_missing_public_response_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"][0]["intended_uses"] = [
            "MODEL_PROMPT",
            "RETRIEVAL",
        ]
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_23_missing_model_prompt_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"][0]["intended_uses"] = [
            "PUBLIC_RESPONSE",
            "RETRIEVAL",
        ]
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_24_missing_retrieval_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"][0]["intended_uses"] = [
            "PUBLIC_RESPONSE",
            "MODEL_PROMPT",
        ]
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_25_training_dataset_allowed_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"][0]["intended_uses"] = [
            "PUBLIC_RESPONSE",
            "MODEL_PROMPT",
            "RETRIEVAL",
            "TRAINING_DATASET",
        ]
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_26_missing_training_prohibition_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"][0]["prohibited_uses"] = []
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_27_personal_email_not_excluded_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"][0]["personal_email"] = "visible"
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_28_personal_phone_not_excluded_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"][0]["personal_phone"] = "visible"
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_29_personal_address_not_excluded_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"][0]["personal_address"] = "visible"
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_30_wrong_approved_by_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"][0]["approved_by"] = "person:other"
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_31_fourth_record_fails(self) -> None:
        payload = _default_registry_dict()
        extra = dict(payload["records"][0])
        extra["subject_id"] = "org:unexpected-fourth"
        extra["statement"] = "Unexpected fourth approved record statement."
        payload["records"].append(extra)
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_32_missing_required_record_fails(self) -> None:
        payload = _default_registry_dict()
        payload["records"] = [payload["records"][0], payload["records"][1]]
        path = _write_registry(self._tmp, payload)
        with self.assertRaises(ApprovedIdentityRegistryError):
            load_approved_identity_registry(path)

    def test_33_exact_subject_lookup(self) -> None:
        registry = load_approved_identity_registry()
        rec = registry.get_by_subject_id("product:siona")
        self.assertIsNotNone(rec)
        self.assertEqual(rec.statement, STMT_PRODUCT)

    def test_34_unknown_subject_lookup(self) -> None:
        registry = load_approved_identity_registry()
        self.assertIsNone(registry.get_by_subject_id("person:unknown"))
        self.assertIsNone(registry.get_by_subject_id("product:sio"))

    def test_35_duplicate_requested_ids_one_record(self) -> None:
        registry = load_approved_identity_registry()
        selected = registry.select_by_subject_ids(
            ("product:siona", "product:siona")
        )
        self.assertEqual(len(selected), 1)

    def test_36_more_than_sixteen_requested_ids_fail(self) -> None:
        registry = load_approved_identity_registry()
        ids = [f"org:req-{i:02d}" for i in range(MAX_SELECT_SUBJECT_IDS + 1)]
        with self.assertRaises(ApprovedIdentityRegistryError):
            registry.select_by_subject_ids(ids)

    def test_37_no_fuzzy_matching(self) -> None:
        registry = load_approved_identity_registry()
        self.assertIsNone(registry.get_by_subject_id("siona"))
        self.assertIsNone(registry.get_by_subject_id("samson"))

    def test_38_public_response_policy_permits(self) -> None:
        registry = load_approved_identity_registry()
        for record in registry.all_records():
            decision = decide_public(
                record, requested_use=AllowedUse.PUBLIC_RESPONSE
            )
            self.assertTrue(decision.allowed, record.subject_id)

    def test_39_model_prompt_policy_permits(self) -> None:
        registry = load_approved_identity_registry()
        ctx = _guest_ctx()
        for record in registry.all_records():
            decision = decide_model_prompt(record, ctx=ctx)
            self.assertTrue(decision.allowed, record.subject_id)

    def test_40_training_policy_denies(self) -> None:
        registry = load_approved_identity_registry()
        for record in registry.all_records():
            decision = decide_training(record)
            self.assertFalse(decision.allowed)

    def test_41_public_website_not_intended(self) -> None:
        registry = load_approved_identity_registry()
        for record in registry.all_records():
            self.assertNotIn(AllowedUse.PUBLIC_WEBSITE, record.intended_uses)

    def test_42_governed_context_integration(self) -> None:
        registry = load_approved_identity_registry()
        selected = registry.select_by_subject_ids(
            (
                "company:siona-technologies",
                "product:siona",
                "person:samson-sibona-njaji",
            )
        )
        result = GovernedContextAssembler().assemble(
            GovernedContextInput(
                records=tuple(selected),
                policy_context=_guest_ctx(),
                audience=ContextAudience.PUBLIC_RESPONSE,
            )
        )
        self.assertEqual(result.included_count, 3)
        for stmt in APPROVED_STATEMENTS:
            self.assertIn(stmt, result.context_text)

    def test_43_no_automatic_language_engine_injection(self) -> None:
        os.environ.pop(ENV_GOVERNED, None)
        engine = LanguageEngine(provider=LocalDummyLLMProvider())
        out = engine.process("Approved identity probe", role="GUEST")
        blob = json.dumps(out)
        for stmt in APPROVED_STATEMENTS:
            self.assertNotIn(stmt, blob)

    def test_44_unselected_records_not_in_prompt(self) -> None:
        registry = load_approved_identity_registry()
        selected = registry.select_by_subject_ids(("product:siona",))
        result = GovernedContextAssembler().assemble(
            GovernedContextInput(
                records=tuple(selected),
                policy_context=_guest_ctx(),
                audience=ContextAudience.PUBLIC_RESPONSE,
            )
        )
        self.assertIn(STMT_PRODUCT, result.context_text)
        self.assertNotIn(STMT_COMPANY, result.context_text)
        self.assertNotIn(STMT_PERSON, result.context_text)

    def test_45_no_network_access(self) -> None:
        import ssn.governance.identity_registry as mod

        source = Path(mod.__file__).read_text(encoding="utf-8")
        self.assertNotIn("urllib", source)
        self.assertNotIn("requests", source)
        self.assertNotIn("httpx", source)
        self.assertIn("open(\"rb\")", source.replace("'", '"'))

    def test_46_no_subprocess_starts(self) -> None:
        with mock.patch("subprocess.Popen") as popen:
            load_approved_identity_registry()
            popen.assert_not_called()

    def test_47_no_llama_process(self) -> None:
        try:
            out = subprocess.run(
                ["pgrep", "-fl", "llama"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            self.assertFalse(out.stdout.strip())
        except FileNotFoundError:
            pass

    def test_48_no_model_file_read_or_modify(self) -> None:
        gguf = list(ROOT.rglob("*.gguf"))
        touched: List[str] = []
        for path in gguf[:5]:
            before = path.stat().st_mtime_ns
            load_approved_identity_registry()
            after = path.stat().st_mtime_ns
            touched.append(path.name)
            self.assertEqual(before, after)

    def test_49_no_ssn_data_read_or_modify(self) -> None:
        load_approved_identity_registry()
        if DATA_DIR.is_dir():
            self.assertEqual(
                tuple(sorted(p.name for p in DATA_DIR.iterdir())),
                self._data_listing,
            )

    def test_50_world_model_untouched(self) -> None:
        load_approved_identity_registry()
        if WORLD_MODEL.exists() and self._world_mtime is not None:
            self.assertEqual(
                WORLD_MODEL.stat().st_mtime_ns, self._world_mtime
            )

    def test_privacy_scan_registry_content(self) -> None:
        registry = load_approved_identity_registry()
        blob = json.dumps(
            [r.to_dict() for r in registry.all_records()],
            ensure_ascii=False,
        )
        for pattern in SENSITIVE_PATTERNS:
            self.assertIsNone(pattern.search(blob))


if __name__ == "__main__":
    unittest.main()
