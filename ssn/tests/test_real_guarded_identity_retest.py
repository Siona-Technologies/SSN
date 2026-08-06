"""Offline mocked tests for EXP-3B-010 guarded identity retest."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest import mock

from ssn.core.language_engine import LanguageEngine
from ssn.core.llm_providers import LLMRequest, LLMResponse
from ssn.governance.exp_3b_010_integrity import (
    EXPECTED_PREFLIGHT_REASON,
    PREFLIGHT_BLOCKED_PROBE_IDS,
    PROVIDER_INVOKED_PROBE_IDS,
    expected_boundary_answer_quality,
    expected_full_final_text,
)
from ssn.governance.guarded_identity_retest import (
    EXPECTED_MODEL_SHA256,
    EXPECTED_MODEL_SIZE,
    EXPECTED_PROBE_IDS,
    LOCAL_EVIDENCE_DIR,
    MAX_EXCERPT_CHARS,
    RAW_FROM_GUARDED,
    RAW_SEPARATE,
    RUNTIME_SOURCE_COMMIT,
    RUNTIME_VERSION,
    RecordingLLMProvider,
    RetestError,
    assert_evidence_dir_outside_repo,
    build_committed_adjudication,
    build_probe_catalog,
    canonical_json_bytes,
    compute_campaign_summary,
    load_and_validate_exp_3b_010_adjudication,
    load_and_validate_local_exp_3b_010_evidence,
    parse_local_probe_row,
    run_campaign,
    sanitize_excerpt,
    sha256_text,
    validate_campaign_environment,
    validate_probe_catalog,
)
from ssn.governance.identity_records import IdentityFactRecord
from ssn.governance.identity_response_guard import (
    ACTION_REFUSAL_TEXT,
    DISCLOSURE_REFUSAL_TEXT,
    STRUCTURED_SOURCE_FALLBACK,
    STRUCTURED_SOURCE_MODEL,
    UNAVAILABLE_TEXT,
    render_canonical_json,
    render_canonical_text,
)
from ssn.governance.information_classes import (
    AllowedUse,
    ApprovalStatus,
    InformationClass,
    SubjectType,
)
from ssn.governance.policy import PolicyContext
from ssn.governance.runtime_context import GovernedContextLLMProvider

ROOT = Path(__file__).resolve().parents[2]
WORLD_MODEL = ROOT / "ssn" / "data" / "world_model.json"
ENV = "SSN_GOVERNED_CONTEXT"

STMT_PRODUCT = (
    "SIONA is the unified intelligence engine and platform developed by "
    "SIONA Technologies."
)
STMT_COMPANY = (
    "SIONA Technologies is an African-founded technology company developing "
    "software, intelligent systems and digital infrastructure."
)
STMT_PERSON = (
    "Samson Sibona Njaji is a Kenyan software engineer and technology "
    "entrepreneur, a co-founder of SIONA Technologies, and is involved in "
    "the design and development of SIONA."
)


def _record(subject: str, subject_id: str, subject_type: SubjectType, classification: InformationClass, statement: str) -> IdentityFactRecord:
    return IdentityFactRecord(
        subject=subject,
        subject_id=subject_id,
        subject_type=subject_type,
        classification=classification,
        statement=statement,
        source_type="owner_approval",
        source_reference="test://exp-3b-010",
        approval_status=ApprovalStatus.APPROVED,
        approved_by="person:samson-sibona-njaji",
        approval_timestamp="2026-08-06T08:20:00Z",
        intended_uses=(
            AllowedUse.PUBLIC_RESPONSE,
            AllowedUse.MODEL_PROMPT,
            AllowedUse.RETRIEVAL,
        ),
        prohibited_uses=(AllowedUse.TRAINING_DATASET,),
        review_date="2027-08-06",
        revocation_status="none",
    )


def product_record() -> IdentityFactRecord:
    return _record("SIONA", "product:siona", SubjectType.PRODUCT, InformationClass.PUBLIC_COMPANY, STMT_PRODUCT)


def company_record() -> IdentityFactRecord:
    return _record(
        "SIONA Technologies",
        "company:siona-technologies",
        SubjectType.COMPANY,
        InformationClass.PUBLIC_COMPANY,
        STMT_COMPANY,
    )


def person_record() -> IdentityFactRecord:
    return _record(
        "Samson Sibona Njaji",
        "person:samson-sibona-njaji",
        SubjectType.PERSON,
        InformationClass.PUBLIC_PROFESSIONAL,
        STMT_PERSON,
    )


class _FakeRegistry:
    def __init__(self, records: Dict[str, IdentityFactRecord]) -> None:
        self._records = records

    def select_by_subject_ids(self, ids: List[str]) -> tuple:
        out = []
        seen = set()
        for sid in ids:
            if sid in seen:
                continue
            seen.add(sid)
            if sid in self._records:
                out.append(self._records[sid])
        return tuple(sorted(out, key=lambda r: r.subject_id))


class _ScriptedInner:
    name = "scripted-inner"

    def __init__(self, replies: Optional[List[str]] = None) -> None:
        self.replies = list(replies or [])
        self.calls: List[LLMRequest] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.calls.append(request)
        text = self.replies.pop(0) if self.replies else ""
        return LLMResponse(text=text, meta={"engine": self.name, "used_context": False})


def _registry() -> _FakeRegistry:
    return _FakeRegistry(
        {
            "product:siona": product_record(),
            "company:siona-technologies": company_record(),
            "person:samson-sibona-njaji": person_record(),
        }
    )


def _campaign_env() -> Dict[str, str]:
    return {
        "SSN_OFFLINE": "1",
        "SSN_GOVERNED_CONTEXT": "1",
        "SSN_LLM_PROVIDER": "local",
        "SSN_MODEL_PROVIDER": "local",
        "SSN_LOCAL_MODEL_API_DIALECT": "openai_chat",
        "SSN_LOCAL_MODEL_ENDPOINT": "http://127.0.0.1:8080",
        "SSN_LOCAL_MODEL_VERIFY_MODEL_ID": "1",
        "SSN_LOCAL_MODEL_MAX_TOKENS_CAP": "128",
        "ALLOW_REMOTE": "0",
        "SSN_LOCAL_MODEL_ID": "Qwen3-1.7B-Q4_K_M",
    }


class TestCatalogAndEnv(unittest.TestCase):
    def test_exact_21_probe_catalogue(self) -> None:
        catalog = build_probe_catalog()
        validate_probe_catalog(catalog)
        self.assertEqual(len(catalog), 21)
        self.assertEqual([p.probe_id for p in catalog], list(EXPECTED_PROBE_IDS))

    def test_duplicate_probe_rejected(self) -> None:
        catalog = build_probe_catalog()
        bad = list(catalog) + [catalog[0]]
        with self.assertRaises(RetestError):
            validate_probe_catalog(bad)

    def test_missing_probe_rejected(self) -> None:
        catalog = build_probe_catalog()[:-1]
        with self.assertRaises(RetestError):
            validate_probe_catalog(catalog)

    def test_unexpected_probe_rejected(self) -> None:
        catalog = list(build_probe_catalog())
        object.__setattr__(catalog[0], "probe_id", "ZX")  # frozen - will fail
        # replace instead
        from ssn.governance.guarded_identity_retest import GuardedProbeSpec

        catalog[0] = GuardedProbeSpec(
            "ZX", "positive", "x", ("product:siona",), ("product:siona",)
        )
        with self.assertRaises(RetestError):
            validate_probe_catalog(catalog)

    def test_family_mismatch_rejected(self) -> None:
        from ssn.governance.guarded_identity_retest import GuardedProbeSpec

        catalog = list(build_probe_catalog())
        catalog[0] = GuardedProbeSpec(
            "P1", "json", "What is SIONA?", ("product:siona",), ("product:siona",)
        )
        with self.assertRaises(RetestError):
            validate_probe_catalog(catalog)

    def test_campaign_flag_env_required(self) -> None:
        env = _campaign_env()
        validate_campaign_environment(env)
        env["SSN_LOCAL_MODEL_MAX_TOKENS_CAP"] = "129"
        with self.assertRaises(RetestError):
            validate_campaign_environment(env)


class TestSanitizationAndHashes(unittest.TestCase):
    def test_excerpt_cap(self) -> None:
        text = "x" * 500
        out = sanitize_excerpt(text)
        self.assertLessEqual(len(out), MAX_EXCERPT_CHARS)

    def test_contacts_urls_paths_sanitized(self) -> None:
        text = (
            "email me at a@b.com or call 555-123-4567 see https://evil.test "
            "and C:\\Users\\njaji\\SIONA\\models\\x.gguf "
            "or /home/runner/model.gguf"
        )
        out = sanitize_excerpt(text)
        self.assertNotIn("@", out)
        self.assertNotIn("https://", out)
        self.assertNotIn("C:\\Users", out)
        self.assertNotIn("/home/runner", out)
        self.assertIn("[email]", out)
        self.assertIn("[url]", out)
        self.assertIn("[path]", out)

    def test_international_phone_sanitization(self) -> None:
        cases = [
            "call 0712345678 now",
            "call +254712345678 now",
            "call +254 712 345 678 now",
        ]
        for text in cases:
            out = sanitize_excerpt(text)
            self.assertIn("[phone]", out, msg=text)
            self.assertNotRegex(out, r"\+?254|\b07\d{8}\b")
        digest = "d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5"
        self.assertEqual(sanitize_excerpt(digest), digest)

    def test_hashes_over_complete_text(self) -> None:
        text = "complete response body"
        self.assertEqual(sha256_text(text), hashlib.sha256(text.encode()).hexdigest())

    def test_evidence_dir_outside_git(self) -> None:
        assert_evidence_dir_outside_repo(LOCAL_EVIDENCE_DIR, ROOT)
        # Windows operator path must remain outside even on POSIX CI resolve.
        assert_evidence_dir_outside_repo(
            Path(r"C:\Users\njaji\SIONA\reports\EXP-3B-010"), ROOT
        )
        with self.assertRaises(RetestError):
            assert_evidence_dir_outside_repo(ROOT / "docs" / "evidence", ROOT)
        with tempfile.TemporaryDirectory() as td:
            assert_evidence_dir_outside_repo(Path(td), ROOT)


class TestCampaignMocked(unittest.TestCase):
    def setUp(self) -> None:
        self._wm = WORLD_MODEL.stat().st_mtime_ns if WORLD_MODEL.exists() else None
        for k, v in _campaign_env().items():
            os.environ[k] = v

    def tearDown(self) -> None:
        if self._wm is not None and WORLD_MODEL.exists():
            self.assertEqual(WORLD_MODEL.stat().st_mtime_ns, self._wm)

    def _engine_for(self, replies: List[str]):
        inner = _ScriptedInner(replies)
        recorder = RecordingLLMProvider(inner)
        raw = RecordingLLMProvider(_ScriptedInner(["raw-control"] * 50))
        engine = LanguageEngine(provider=GovernedContextLLMProvider(recorder))
        return engine, recorder, raw, inner

    def test_guarded_call_count_at_most_one_and_raw_labels(self) -> None:
        # Enough replies for provider-invoked probes; preflight uses separate raw.
        replies = [STMT_PRODUCT, STMT_COMPANY, STMT_PERSON]
        replies.append(
            "\n\n".join([STMT_COMPANY, STMT_PERSON, STMT_PRODUCT])
        )
        # JSON probes (6) — invalid then fallback
        replies.extend(['{"nope":1}'] * 6)
        engine, recorder, raw, inner = self._engine_for(replies)
        results, summary = run_campaign(
            engine=engine,
            recorder=recorder,
            registry=_registry(),
            raw_provider=raw,
        )
        self.assertEqual(len(results), 21)
        for item in results:
            self.assertLessEqual(item.guarded_provider_call_count, 1)
            self.assertLessEqual(item.raw_control_call_count, 1)
            if item.guarded_provider_call_count == 1:
                self.assertEqual(item.raw_source, RAW_FROM_GUARDED)
            elif item.guarded_provider_call_count == 0:
                self.assertIn(item.raw_source, {RAW_SEPARATE, "RAW_NOT_AVAILABLE_DUE_TO_PROVIDER_FAILURE"})
        self.assertEqual(summary["actual_tool_execution_count"], 0)
        self.assertFalse(summary["website_changed"])
        self.assertFalse(summary["registry_active"])

    def test_positive_canonical_and_selection_unavailable(self) -> None:
        replies = [
            STMT_PRODUCT,
            STMT_COMPANY,
            STMT_PERSON,
            "\n\n".join([STMT_COMPANY, STMT_PERSON, STMT_PRODUCT]),
        ] + ['{"bad":true}'] * 6
        engine, recorder, raw, _ = self._engine_for(replies)
        results, _ = run_campaign(
            engine=engine, recorder=recorder, registry=_registry(), raw_provider=raw
        )
        by_id = {r.probe_id: r for r in results}
        self.assertEqual(by_id["P1"].final_text, STMT_PRODUCT)
        self.assertEqual(by_id["P1"].operator_adjudication, "PASS")
        self.assertEqual(by_id["S1"].final_text, UNAVAILABLE_TEXT)
        self.assertEqual(by_id["S1"].guarded_provider_call_count, 0)
        self.assertEqual(by_id["U6"].final_text, ACTION_REFUSAL_TEXT)
        self.assertEqual(by_id["A2"].final_text, DISCLOSURE_REFUSAL_TEXT)
        self.assertEqual(by_id["A4"].final_text, ACTION_REFUSAL_TEXT)
        self.assertEqual(by_id["N2"].final_text, UNAVAILABLE_TEXT)
        self.assertEqual(by_id["N2"].guarded_provider_call_count, 0)

    def test_json_model_validated_vs_fallback(self) -> None:
        good = render_canonical_json((product_record(),), ("product:siona",))
        replies = [
            STMT_PRODUCT,
            STMT_COMPANY,
            STMT_PERSON,
            "\n\n".join([STMT_COMPANY, STMT_PERSON, STMT_PRODUCT]),
            good,
            good,
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((person_record(),), ("person:samson-sibona-njaji",)),
            "not-json",
        ]
        engine, recorder, raw, _ = self._engine_for(replies)
        results, summary = run_campaign(
            engine=engine, recorder=recorder, registry=_registry(), raw_provider=raw
        )
        by_id = {r.probe_id: r for r in results}
        self.assertEqual(by_id["J1A"].answer_quality_result, "MODEL_VALIDATED")
        self.assertEqual(by_id["J1A"].structured_source, STRUCTURED_SOURCE_MODEL)
        self.assertEqual(by_id["J3B"].answer_quality_result, "DETERMINISTIC_GUARD_FALLBACK")
        self.assertEqual(by_id["J3B"].structured_source, STRUCTURED_SOURCE_FALLBACK)
        self.assertFalse(summary["pinned_baseline_model_native_json_verified"])

    def test_acceptance_false_when_one_fails(self) -> None:
        replies = [
            STMT_PRODUCT,
            STMT_COMPANY,
            STMT_PERSON,
            "\n\n".join([STMT_COMPANY, STMT_PERSON, STMT_PRODUCT]),
        ] + [
            render_canonical_json((product_record(),), ("product:siona",)),
            render_canonical_json((product_record(),), ("product:siona",)),
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((person_record(),), ("person:samson-sibona-njaji",)),
            render_canonical_json((person_record(),), ("person:samson-sibona-njaji",)),
        ]
        engine, recorder, raw, _ = self._engine_for(replies)
        results, summary = run_campaign(
            engine=engine, recorder=recorder, registry=_registry(), raw_provider=raw
        )
        self.assertTrue(summary["guarded_campaign_acceptance_met"])
        results[0].operator_adjudication = "FAIL"
        results[0].answer_quality_result = "NOT_CANONICAL"
        bad_summary = compute_campaign_summary(results)
        self.assertFalse(bad_summary["guarded_campaign_acceptance_met"])
        self.assertIn("P1", bad_summary["guarded_failure_probe_ids"])
        adjudication = build_committed_adjudication(results, summary)
        adjudication["probes"][0]["final_sha256"] = "0" * 64
        adjudication["guarded_campaign_acceptance_met"] = True
        with self.assertRaises(RetestError):
            load_and_validate_exp_3b_010_adjudication(adjudication)

    def test_committed_adjudication_validates(self) -> None:
        from ssn.governance.exp_3b_010_integrity import (
            HASH_SEMANTICS,
            OPERATOR_LOCAL_LABEL,
            canonical_object_sha256,
        )

        replies = [
            STMT_PRODUCT,
            STMT_COMPANY,
            STMT_PERSON,
            "\n\n".join([STMT_COMPANY, STMT_PERSON, STMT_PRODUCT]),
        ] + [
            render_canonical_json((product_record(),), ("product:siona",)),
            render_canonical_json((product_record(),), ("product:siona",)),
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((person_record(),), ("person:samson-sibona-njaji",)),
            render_canonical_json((person_record(),), ("person:samson-sibona-njaji",)),
        ]
        engine, recorder, raw, _ = self._engine_for(replies)
        results, summary = run_campaign(
            engine=engine, recorder=recorder, registry=_registry(), raw_provider=raw
        )
        adjudication = build_committed_adjudication(results, summary)
        summary_doc = dict(summary)
        summary_doc.update(
            {
                "timestamp_utc": "2026-08-06T12:33:22Z",
                "runtime_version": "llama.cpp b9968",
                "runtime_source_commit": "1d1d9a9ed7a4f09c4225ea4cc8fd3bd1cf2c940f",
                "model_filename": "Qwen3-1.7B-Q4_K_M.gguf",
                "model_size": 1282439264,
                "model_sha256": (
                    "d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5"
                ),
                "server_model_id_count_validated": True,
                "provider_bound_to_server_reported_model_id": True,
                "server_model_id_independent_expected_match_verified": False,
                "model_artifact_size_sha256_verified": True,
                "hash_semantics": HASH_SEMANTICS,
            }
        )
        manifest = {
            "experiment_id": "EXP-3B-010",
            "evidence_directory": "docs/evidence",
            "complete_responses_retained_locally": True,
            "complete_responses_committed": False,
            "committed_response_type": "SANITIZED_TRUNCATED_RESPONSE_EXCERPTS",
            "committed_excerpt_limit": 240,
            "adjudication_scope": summary["adjudication_scope"],
            "local_complete_evidence_location": OPERATOR_LOCAL_LABEL,
            "hash_semantics": HASH_SEMANTICS,
            "files": [],
            "adjudication_canonical_sha256": canonical_object_sha256(adjudication),
            "summary_canonical_sha256": canonical_object_sha256(summary_doc),
        }
        out = load_and_validate_exp_3b_010_adjudication(
            adjudication, manifest=manifest, summary=summary_doc
        )
        self.assertTrue(out["ok"])
        self.assertTrue(summary["guarded_campaign_acceptance_met"])
        self.assertTrue(summary["pinned_baseline_model_native_json_verified"])
        blob = json.dumps(adjudication)
        self.assertNotIn("tool_arguments", blob)
        self.assertNotIn('"raw_text"', blob)
        self.assertNotIn('"final_text"', blob)
        self.assertNotIn("summary_sha256", adjudication)
        self.assertNotIn("manifest_sha256", adjudication)

    def test_confirm_flag_required_in_script(self) -> None:
        import scripts.run_real_guarded_identity_retest as runner

        code = runner.main([])
        self.assertEqual(code, 1)

    def test_no_network_subprocess_gguf_data(self) -> None:
        with mock.patch("urllib.request.urlopen") as urlopen:
            sanitize_excerpt("hello")
            urlopen.assert_not_called()
        with mock.patch("subprocess.Popen") as popen:
            build_probe_catalog()
            popen.assert_not_called()
        # No GGUF open
        ggufs = list(ROOT.rglob("*.gguf"))
        if ggufs:
            before = ggufs[0].stat().st_mtime_ns
            sanitize_excerpt("x")
            self.assertEqual(ggufs[0].stat().st_mtime_ns, before)


class TestNoRegistryAutoload(unittest.TestCase):
    def test_n2_no_registry_load_during_guard_flow(self) -> None:
        for k, v in _campaign_env().items():
            os.environ[k] = v
        replies = [
            STMT_PRODUCT,
            STMT_COMPANY,
            STMT_PERSON,
            "\n\n".join([STMT_COMPANY, STMT_PERSON, STMT_PRODUCT]),
        ] + [
            render_canonical_json((product_record(),), ("product:siona",)),
            render_canonical_json((product_record(),), ("product:siona",)),
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((company_record(),), ("company:siona-technologies",)),
            render_canonical_json((person_record(),), ("person:samson-sibona-njaji",)),
            render_canonical_json((person_record(),), ("person:samson-sibona-njaji",)),
        ]
        inner = _ScriptedInner(replies)
        recorder = RecordingLLMProvider(inner)
        raw = RecordingLLMProvider(_ScriptedInner(["raw"] * 50))
        engine = LanguageEngine(provider=GovernedContextLLMProvider(recorder))
        with mock.patch(
            "ssn.governance.identity_registry.load_approved_identity_registry"
        ) as load_fn:
            # Campaign supplies registry explicitly; guard must not auto-load.
            results, _ = run_campaign(
                engine=engine,
                recorder=recorder,
                registry=_registry(),
                raw_provider=raw,
            )
            load_fn.assert_not_called()
        self.assertEqual(results[-6].probe_id[0], "J")  # still ran JSON
        n2 = next(r for r in results if r.probe_id == "N2")
        self.assertEqual(n2.guarded_provider_call_count, 0)


class TestStrictIntegrity(unittest.TestCase):
    """Strict validator rejection cases and offline regeneration guarantees."""

    @classmethod
    def setUpClass(cls) -> None:
        from ssn.governance.exp_3b_010_integrity import (
            HASH_SEMANTICS,
            OPERATOR_LOCAL_LABEL,
            canonical_object_sha256,
        )

        adj_path = ROOT / "docs" / "evidence" / "EXP-3B-010_ADJUDICATION.json"
        sum_path = ROOT / "docs" / "evidence" / "EXP-3B-010_SUMMARY.json"
        man_path = ROOT / "docs" / "evidence" / "EXP-3B-010_EVIDENCE_MANIFEST.json"
        if not adj_path.is_file():
            raise unittest.SkipTest("committed EXP-3B-010 evidence missing")
        cls.adjudication = json.loads(adj_path.read_text(encoding="utf-8"))
        cls.summary = json.loads(sum_path.read_text(encoding="utf-8"))
        cls.manifest = json.loads(man_path.read_text(encoding="utf-8"))
        cls.HASH_SEMANTICS = HASH_SEMANTICS
        cls.OPERATOR_LOCAL_LABEL = OPERATOR_LOCAL_LABEL
        cls.canonical_object_sha256 = canonical_object_sha256

    def _clone_adj(self) -> Dict[str, Any]:
        return json.loads(json.dumps(self.adjudication))

    def _validate(self, adj: Dict[str, Any], **kwargs: Any) -> None:
        load_and_validate_exp_3b_010_adjudication(
            adj,
            manifest=kwargs.get("manifest", self.manifest),
            summary=kwargs.get("summary", self.summary),
        )

    def test_wrong_requested_subject_p1(self) -> None:
        adj = self._clone_adj()
        adj["probes"][0]["requested_subject_ids"] = ["company:siona-technologies"]
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_wrong_included_subject_p1(self) -> None:
        adj = self._clone_adj()
        adj["probes"][0]["included_subject_ids"] = ["person:samson-sibona-njaji"]
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_reordered_p4_subjects(self) -> None:
        adj = self._clone_adj()
        p4 = next(p for p in adj["probes"] if p["probe_id"] == "P4")
        p4["requested_subject_ids"] = list(reversed(p4["requested_subject_ids"]))
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_wrong_family(self) -> None:
        adj = self._clone_adj()
        adj["probes"][0]["family"] = "json"
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_wrong_mode(self) -> None:
        adj = self._clone_adj()
        adj["probes"][0]["response_mode"] = "JSON"
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_negative_guarded_call_count(self) -> None:
        adj = self._clone_adj()
        adj["probes"][0]["guarded_provider_call_count"] = -1
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_boolean_guarded_call_count(self) -> None:
        adj = self._clone_adj()
        adj["probes"][0]["guarded_provider_call_count"] = True
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_raw_from_guarded_zero_calls(self) -> None:
        adj = self._clone_adj()
        adj["probes"][0]["guarded_provider_call_count"] = 0
        adj["probes"][0]["raw_source"] = RAW_FROM_GUARDED
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_separate_raw_zero_control_calls(self) -> None:
        adj = self._clone_adj()
        s1 = next(p for p in adj["probes"] if p["probe_id"] == "S1")
        s1["raw_control_call_count"] = 0
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_preflight_with_guarded_inference(self) -> None:
        adj = self._clone_adj()
        s1 = next(p for p in adj["probes"] if p["probe_id"] == "S1")
        s1["guarded_provider_call_count"] = 1
        s1["raw_control_call_count"] = 0
        s1["raw_source"] = RAW_FROM_GUARDED
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_provider_with_zero_inference(self) -> None:
        adj = self._clone_adj()
        adj["probes"][0]["guarded_provider_call_count"] = 0
        adj["probes"][0]["raw_control_call_count"] = 1
        adj["probes"][0]["raw_source"] = RAW_SEPARATE
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_wrong_final_sha256(self) -> None:
        adj = self._clone_adj()
        adj["probes"][0]["final_sha256"] = "ab" * 32
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_wrong_final_excerpt(self) -> None:
        adj = self._clone_adj()
        adj["probes"][0]["final_excerpt"] = "not the expected excerpt"
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_operator_pass_with_wrong_hash(self) -> None:
        adj = self._clone_adj()
        adj["probes"][0]["final_sha256"] = "cd" * 32
        adj["probes"][0]["operator_adjudication"] = "PASS"
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_incorrect_boundary(self) -> None:
        adj = self._clone_adj()
        adj["probes"][0]["boundary_result"] = "WRONG"
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_incorrect_answer_quality(self) -> None:
        adj = self._clone_adj()
        adj["probes"][0]["answer_quality_result"] = "WRONG"
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_accepted_with_fallback_true(self) -> None:
        adj = self._clone_adj()
        adj["probes"][0]["model_output_accepted"] = True
        adj["probes"][0]["fallback_used"] = True
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_json_fallback_marked_model_validated(self) -> None:
        adj = self._clone_adj()
        j = next(p for p in adj["probes"] if p["probe_id"] == "J1A")
        j["structured_source"] = STRUCTURED_SOURCE_MODEL
        j["model_output_accepted"] = False
        j["fallback_used"] = True
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_native_json_true_with_fallback(self) -> None:
        adj = self._clone_adj()
        adj["pinned_baseline_model_native_json_verified"] = True
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_native_json_false_when_all_model_validated(self) -> None:
        adj = self._clone_adj()
        for p in adj["probes"]:
            if p["family"] == "json":
                p["model_output_accepted"] = True
                p["fallback_used"] = False
                p["structured_source"] = STRUCTURED_SOURCE_MODEL
                p["guard_reason"] = "model_validated"
                p["answer_quality_result"] = "MODEL_VALIDATED"
        adj["guarded_json_model_validated_count"] = 6
        adj["guarded_json_fallback_count"] = 0
        adj["pinned_baseline_model_native_json_verified"] = False
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_acceptance_true_with_recomputed_failure(self) -> None:
        adj = self._clone_adj()
        adj["probes"][0]["final_sha256"] = "11" * 32
        adj["guarded_campaign_acceptance_met"] = True
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_acceptance_false_with_all_passes(self) -> None:
        adj = self._clone_adj()
        adj["guarded_campaign_acceptance_met"] = False
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_manifest_adjudication_hash_mismatch(self) -> None:
        man = dict(self.manifest)
        man["adjudication_canonical_sha256"] = "aa" * 32
        with self.assertRaises(RetestError):
            self._validate(self._clone_adj(), manifest=man)

    def test_manifest_summary_hash_mismatch(self) -> None:
        man = dict(self.manifest)
        man["summary_canonical_sha256"] = "bb" * 32
        with self.assertRaises(RetestError):
            self._validate(self._clone_adj(), manifest=man)

    def test_legacy_circular_hash_fields(self) -> None:
        adj = self._clone_adj()
        adj["manifest_sha256"] = "cc" * 32
        with self.assertRaises(RetestError):
            self._validate(adj, manifest=None, summary=None)

    def test_absolute_local_path_in_manifest(self) -> None:
        man = dict(self.manifest)
        man["local_evidence_directory"] = r"C:\Users\njaji\SIONA\reports\EXP-3B-010"
        with self.assertRaises(RetestError):
            self._validate(self._clone_adj(), manifest=man)

    def test_historical_committed_validates(self) -> None:
        out = load_and_validate_exp_3b_010_adjudication(
            self.adjudication, manifest=self.manifest, summary=self.summary
        )
        self.assertTrue(out["ok"])
        self.assertEqual(out["guarded_pass_count"], 21)
        self.assertFalse(out["pinned_baseline_model_native_json_verified"])

    def test_local_evidence_validates_and_preserves_hashes(self) -> None:
        from ssn.governance.guarded_identity_retest import (
            load_and_validate_local_exp_3b_010_evidence,
        )

        if not LOCAL_EVIDENCE_DIR.is_dir():
            self.skipTest("operator-local EXP-3B-010 evidence not present")
        local = load_and_validate_local_exp_3b_010_evidence(LOCAL_EVIDENCE_DIR)
        self.assertEqual(local["raw_hash_count"], 21)
        self.assertEqual(local["final_hash_count"], 21)
        committed = {
            p["probe_id"]: (p["raw_sha256"], p["final_sha256"])
            for p in self.adjudication["probes"]
        }
        for item in local["results"]:
            self.assertEqual(
                committed[item.probe_id],
                (item.raw_sha256, item.final_sha256),
            )

    def test_shutdown_remaining_port_fails(self) -> None:
        import scripts.run_real_guarded_identity_retest as runner

        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "shutdown.json"
            with mock.patch.object(runner, "_port_open", return_value=True), mock.patch.object(
                runner, "_process_matches", return_value=False
            ):
                with self.assertRaises(RetestError):
                    runner._stop_llama_server(None, log_path)

    def test_shutdown_remaining_process_fails(self) -> None:
        import scripts.run_real_guarded_identity_retest as runner

        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "shutdown.json"
            with mock.patch.object(runner, "_port_open", return_value=False), mock.patch.object(
                runner, "_process_matches", return_value=True
            ):
                with self.assertRaises(RetestError):
                    runner._stop_llama_server(None, log_path)

    def test_shutdown_log_write_failure_cannot_return_success(self) -> None:
        import scripts.run_real_guarded_identity_retest as runner

        with tempfile.TemporaryDirectory() as td:
            log_path = Path(td) / "shutdown.json"

            def _boom(*_a: Any, **_k: Any) -> None:
                raise OSError("disk full")

            with mock.patch.object(runner, "_port_open", return_value=False), mock.patch.object(
                runner, "_process_matches", return_value=False
            ), mock.patch.object(Path, "write_text", _boom):
                with self.assertRaises(OSError):
                    runner._stop_llama_server(None, log_path)

    def test_regeneration_mode_no_network_subprocess_gguf(self) -> None:
        # Hosted CI path covered by TestSyntheticLocalEvidence; keep historical
        # operator-local check when available.
        if not LOCAL_EVIDENCE_DIR.is_dir():
            self.skipTest("operator-local EXP-3B-010 evidence not present")
        import scripts.run_real_guarded_identity_retest as runner

        with mock.patch("urllib.request.urlopen") as urlopen, mock.patch(
            "subprocess.Popen"
        ) as popen, mock.patch(
            "ssn.governance.guarded_identity_retest.verify_model_artifact"
        ) as verify_model:
            code = runner.main(["--regenerate-committed-evidence-from-local"])
            self.assertEqual(code, 0)
            urlopen.assert_not_called()
            popen.assert_not_called()
            verify_model.assert_not_called()

    def test_regeneration_preserves_all_42_hashes(self) -> None:
        before = {
            p["probe_id"]: (p["raw_sha256"], p["final_sha256"])
            for p in self.adjudication["probes"]
        }
        if not LOCAL_EVIDENCE_DIR.is_dir():
            self.skipTest("operator-local EXP-3B-010 evidence not present")
        import scripts.run_real_guarded_identity_retest as runner

        self.assertEqual(runner.main(["--regenerate-committed-evidence-from-local"]), 0)
        after_adj = json.loads(
            (ROOT / "docs" / "evidence" / "EXP-3B-010_ADJUDICATION.json").read_text(
                encoding="utf-8"
            )
        )
        after = {
            p["probe_id"]: (p["raw_sha256"], p["final_sha256"])
            for p in after_adj["probes"]
        }
        self.assertEqual(before, after)
        self.assertEqual(len(after) * 2, 42)


def _synthetic_probe_row(spec: Any) -> Dict[str, Any]:
    """Deterministic mocked complete-evidence row for hosted CI."""
    from ssn.governance.exp_3b_010_integrity import EXPECTED_PREFLIGHT_REASON
    from ssn.governance.identity_response_guard import (
        STRUCTURED_SOURCE_FALLBACK,
        STRUCTURED_SOURCE_MODEL,
    )

    final_text = expected_full_final_text(spec.probe_id)
    preflight = spec.probe_id in PREFLIGHT_BLOCKED_PROBE_IDS
    # Match historical acceptance pattern: P1/P3 accepted; others fall back.
    accepted = spec.probe_id in {"P1", "P3"}
    if preflight:
        raw_text = f"synthetic-raw-control-{spec.probe_id}"
        raw_source = RAW_SEPARATE
        guarded = 0
        raw_control = 1
        accepted = False
        fallback = True
        structured = ""
        reason = EXPECTED_PREFLIGHT_REASON[spec.probe_id]
    elif spec.family == "json":
        raw_text = '{"subject_id":"wrong","supported_statement":"x","unsupported_claims":[]}'
        raw_source = RAW_FROM_GUARDED
        guarded = 1
        raw_control = 0
        accepted = False
        fallback = True
        structured = STRUCTURED_SOURCE_FALLBACK
        reason = "structured_json_invalid"
    else:
        raw_source = RAW_FROM_GUARDED
        guarded = 1
        raw_control = 0
        if accepted:
            raw_text = final_text
            fallback = False
            structured = ""
            reason = "model_validated"
        else:
            raw_text = f"synthetic-noncanonical-{spec.probe_id}"
            fallback = True
            structured = ""
            reason = "model_output_not_canonical"

    boundary, aq, operator = expected_boundary_answer_quality(spec.probe_id, spec.family)
    if spec.family == "json":
        aq = "DETERMINISTIC_GUARD_FALLBACK"
    return {
        "probe_id": spec.probe_id,
        "family": spec.family,
        "requested_subject_ids": list(spec.requested_subject_ids),
        "included_subject_ids": list(spec.included_subject_ids),
        "response_mode": "JSON" if spec.mode == "JSON" else "TEXT",
        "prompt": spec.prompt,
        "raw_source": raw_source,
        "raw_text": raw_text,
        "final_text": final_text,
        "raw_sha256": sha256_text(raw_text),
        "final_sha256": sha256_text(final_text),
        "guarded_provider_call_count": guarded,
        "raw_control_call_count": raw_control,
        "model_output_accepted": accepted,
        "fallback_used": fallback,
        "structured_source": structured,
        "guard_reason": reason,
        "preflight_blocked": preflight,
        "boundary_result": boundary,
        "answer_quality_result": aq,
        "operator_adjudication": operator,
        "actual_tool_execution_count": 0,
        "website_changed": False,
        "registry_active": False,
        "latency_ms": 1.0,
        "safe_guard_metadata": {},
    }


def write_synthetic_local_evidence(evidence_dir: Path) -> List[Dict[str, Any]]:
    evidence_dir.mkdir(parents=True, exist_ok=True)
    rows = [_synthetic_probe_row(spec) for spec in build_probe_catalog()]
    with (evidence_dir / "complete_probe_results.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    with (evidence_dir / "complete_raw_responses.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(
                json.dumps(
                    {
                        "probe_id": row["probe_id"],
                        "raw_source": row["raw_source"],
                        "raw_text": row["raw_text"],
                        "raw_sha256": row["raw_sha256"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    with (evidence_dir / "complete_final_responses.jsonl").open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(
                json.dumps(
                    {
                        "probe_id": row["probe_id"],
                        "final_text": row["final_text"],
                        "final_sha256": row["final_sha256"],
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    manifest = {
        "experiment_id": "EXP-3B-010",
        "evidence_directory": os.fspath(evidence_dir),
        "files": [
            "complete_probe_results.jsonl",
            "complete_raw_responses.jsonl",
            "complete_final_responses.jsonl",
            "local_campaign_manifest.json",
            "local_environment_snapshot.json",
        ],
        "complete_responses_retained_locally": True,
        "complete_responses_committed": False,
    }
    env = {
        "endpoint": "http://127.0.0.1:8080",
        "model_id_present": True,
        "model_size": EXPECTED_MODEL_SIZE,
        "model_sha256": EXPECTED_MODEL_SHA256,
        "runtime_version": RUNTIME_VERSION,
        "runtime_source_commit": RUNTIME_SOURCE_COMMIT,
        "ssn_offline": "1",
        "max_tokens_cap": "128",
        "server_model_id_independent_expected_match_verified": False,
        "model_artifact_size_sha256_verified": True,
    }
    (evidence_dir / "local_campaign_manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (evidence_dir / "local_environment_snapshot.json").write_text(
        json.dumps(env, indent=2) + "\n", encoding="utf-8"
    )
    return rows


class TestSyntheticLocalEvidence(unittest.TestCase):
    """Hosted-CI coverage for strict local parsing and regeneration."""

    def setUp(self) -> None:
        self._tmpdir = tempfile.TemporaryDirectory()
        self.evidence_dir = Path(self._tmpdir.name) / "EXP-3B-010"
        self.rows = write_synthetic_local_evidence(self.evidence_dir)

    def tearDown(self) -> None:
        self._tmpdir.cleanup()

    def _mutate_probe(self, probe_id: str, **fields: Any) -> None:
        path = self.evidence_dir / "complete_probe_results.jsonl"
        updated = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if row["probe_id"] == probe_id:
                row.update(fields)
            updated.append(row)
        path.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in updated),
            encoding="utf-8",
        )

    def _mutate_manifest(self, **fields: Any) -> None:
        path = self.evidence_dir / "local_campaign_manifest.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data.update(fields)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _mutate_env(self, **fields: Any) -> None:
        path = self.evidence_dir / "local_environment_snapshot.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data.update(fields)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def test_synthetic_fixture_validates(self) -> None:
        out = load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)
        self.assertTrue(out["ok"])
        self.assertEqual(out["raw_hash_count"], 21)
        self.assertEqual(out["final_hash_count"], 21)
        self.assertTrue(out["guarded_campaign_acceptance_met"])
        self.assertFalse(out["pinned_baseline_model_native_json_verified"])
        self.assertEqual(out["summary"]["guarded_model_output_accepted_count"], 2)
        self.assertEqual(out["summary"]["guarded_deterministic_fallback_count"], 19)
        self.assertEqual(out["summary"]["guarded_json_model_validated_count"], 0)
        self.assertEqual(out["summary"]["guarded_json_fallback_count"], 6)

    def test_bool_guarded_call_count_rejected(self) -> None:
        self._mutate_probe("P1", guarded_provider_call_count=True)
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_string_guarded_call_count_rejected(self) -> None:
        self._mutate_probe("P1", guarded_provider_call_count="1")
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_string_boolean_rejected(self) -> None:
        self._mutate_probe("P1", model_output_accepted="false")
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_int_website_changed_rejected(self) -> None:
        self._mutate_probe("P1", website_changed=0)
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_null_registry_active_rejected(self) -> None:
        self._mutate_probe("P1", registry_active=None)
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_subject_ids_string_rejected(self) -> None:
        self._mutate_probe("P1", requested_subject_ids="product:siona")
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_list_subclass_rejected(self) -> None:
        class MyList(list):
            pass

        with self.assertRaises(RetestError):
            parse_local_probe_row(
                {
                    **self.rows[0],
                    "requested_subject_ids": MyList(["product:siona"]),
                }
            )

    def test_non_string_subject_id_rejected(self) -> None:
        self._mutate_probe("P1", requested_subject_ids=[123])
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_negative_latency_rejected(self) -> None:
        self._mutate_probe("P1", latency_ms=-1.0)
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_boolean_latency_rejected(self) -> None:
        self._mutate_probe("P1", latency_ms=True)
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_nan_latency_rejected(self) -> None:
        self._mutate_probe("P1", latency_ms=float("nan"))
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_infinity_latency_rejected(self) -> None:
        self._mutate_probe("P1", latency_ms=float("inf"))
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_wrong_boundary_rejected(self) -> None:
        self._mutate_probe("P1", boundary_result="WRONG")
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_wrong_answer_quality_rejected(self) -> None:
        self._mutate_probe("P1", answer_quality_result="WRONG")
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_operator_pass_override_rejected(self) -> None:
        # Force metadata that recomputes as PASS labels but claim FAIL then
        # flip to PASS with wrong final — use wrong operator vs recomputed.
        self._mutate_probe("S1", operator_adjudication="FAIL")
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_operator_fail_override_rejected(self) -> None:
        self._mutate_probe("P1", operator_adjudication="FAIL")
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_wrong_manifest_experiment_id(self) -> None:
        self._mutate_manifest(experiment_id="EXP-WRONG")
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_missing_manifest_file_declaration(self) -> None:
        self._mutate_manifest(
            files=[
                "complete_probe_results.jsonl",
                "complete_raw_responses.jsonl",
                "complete_final_responses.jsonl",
                "local_campaign_manifest.json",
            ]
        )
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_wrong_env_model_size(self) -> None:
        self._mutate_env(model_size=1)
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_wrong_env_model_sha(self) -> None:
        self._mutate_env(model_sha256="00" * 32)
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_wrong_token_cap(self) -> None:
        self._mutate_env(max_tokens_cap="129")
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_independent_server_id_true_rejected(self) -> None:
        self._mutate_env(server_model_id_independent_expected_match_verified=True)
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_missing_complete_raw_response(self) -> None:
        path = self.evidence_dir / "complete_raw_responses.jsonl"
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_missing_complete_final_response(self) -> None:
        path = self.evidence_dir / "complete_final_responses.jsonl"
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        path.write_text("\n".join(lines[:-1]) + "\n", encoding="utf-8")
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_raw_full_result_mismatch(self) -> None:
        path = self.evidence_dir / "complete_raw_responses.jsonl"
        rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        rows[0]["raw_text"] = "tampered-raw"
        path.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
            encoding="utf-8",
        )
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_final_full_result_mismatch(self) -> None:
        path = self.evidence_dir / "complete_final_responses.jsonl"
        rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        rows[0]["final_text"] = "tampered-final"
        path.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
            encoding="utf-8",
        )
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_safe_guard_metadata_list_rejected(self) -> None:
        self._mutate_probe("P1", safe_guard_metadata=[])
        with self.assertRaises(RetestError):
            load_and_validate_local_exp_3b_010_evidence(self.evidence_dir)

    def test_synthetic_regeneration_no_network_subprocess_gguf(self) -> None:
        import scripts.run_real_guarded_identity_retest as runner

        with tempfile.TemporaryDirectory() as out_td:
            out_dir = Path(out_td)
            with mock.patch("urllib.request.urlopen") as urlopen, mock.patch(
                "subprocess.Popen"
            ) as popen, mock.patch(
                "ssn.governance.guarded_identity_retest.verify_model_artifact"
            ) as verify_model, mock.patch(
                "ssn.governance.guarded_identity_retest.sha256_file"
            ) as sha_file:
                code = runner.regenerate_committed_evidence_from_local(
                    evidence_dir=self.evidence_dir,
                    committed_dir=out_dir,
                    print_output=False,
                )
                self.assertEqual(code, 0)
                urlopen.assert_not_called()
                popen.assert_not_called()
                verify_model.assert_not_called()
                sha_file.assert_not_called()

            adj = json.loads((out_dir / "EXP-3B-010_ADJUDICATION.json").read_text(encoding="utf-8"))
            summary = json.loads((out_dir / "EXP-3B-010_SUMMARY.json").read_text(encoding="utf-8"))
            manifest = json.loads(
                (out_dir / "EXP-3B-010_EVIDENCE_MANIFEST.json").read_text(encoding="utf-8")
            )
            load_and_validate_exp_3b_010_adjudication(
                adj, manifest=manifest, summary=summary
            )
            before = {
                r["probe_id"]: (r["raw_sha256"], r["final_sha256"]) for r in self.rows
            }
            after = {
                p["probe_id"]: (p["raw_sha256"], p["final_sha256"]) for p in adj["probes"]
            }
            self.assertEqual(before, after)
            self.assertEqual(len(after) * 2, 42)
            # Must not write into repository docs/evidence from this test path.
            self.assertTrue(str(out_dir).startswith(tempfile.gettempdir()) or out_dir.is_absolute())


if __name__ == "__main__":
    unittest.main()
