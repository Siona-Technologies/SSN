"""Phase 3A — model registry provenance tests (strict schema)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ssn.cognition.model_gateway.registry import (
    ModelRegistry,
    RegistryValidationError,
    mock_ci_registry_payload,
    validate_entry_dict,
)


def _base(**kwargs):
    data = {
        "provider_id": "provider-a",
        "model_id": "model-a",
        "mock": True,
        "siona_native": False,
    }
    data.update(kwargs)
    return data


class TestModelRegistry(unittest.TestCase):
    def test_valid_manifest(self):
        reg = ModelRegistry()
        reg.load_dict(mock_ci_registry_payload())
        self.assertEqual(len(reg), 1)
        e = reg.get("mock-ci-open-weight")
        self.assertIsNotNone(e)
        self.assertTrue(e.mock)
        self.assertFalse(e.siona_native)

    def test_missing_optional_fields_ok(self):
        entry = validate_entry_dict(_base())
        self.assertIsNone(entry.licence_id)
        self.assertIsNone(entry.artifact_checksum)

    def test_missing_required_fields(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict({"provider_id": "p"})
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict({"model_id": "m"})

    def test_unknown_fields(self):
        with self.assertRaises(RegistryValidationError) as ctx:
            validate_entry_dict(_base(extra_field="nope"))
        self.assertIn("unknown_fields", str(ctx.exception))

    def test_incomplete_licence_pair(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(_base(licence_id="MIT", licence_ref=None))

    def test_negative_context_window(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(_base(context_window=0))
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(_base(context_window=-1))

    def test_invalid_date(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(_base(added_date="not-a-date"))

    def test_invalid_verification_status(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(_base(artifact_verification_status="pretty-sure"))

    def test_explicit_capabilities_verified(self):
        entry = validate_entry_dict(
            _base(
                mock=False,
                artifact_verification_status="unverified",
                capability_verification_status="verified",
                capabilities={
                    "chat": True,
                    "tools": False,
                    "structured_json": True,
                    "streaming": False,
                    "multimodal": False,
                    "context_window": 8192,
                },
                notes="schema fixture only — not a real model",
            )
        )
        self.assertEqual(entry.capability_verification_status, "verified")
        self.assertTrue(entry.capabilities["structured_json"])
        self.assertFalse(entry.capabilities["tools"])
        self.assertEqual(entry.capabilities["context_window"], 8192)

    def test_missing_capabilities_object_when_verified(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                _base(
                    mock=False,
                    capability_verification_status="verified",
                )
            )

    def test_unknown_capability_fields(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                _base(
                    mock=False,
                    capability_verification_status="verified",
                    capabilities={"chat": True, "telepathy": True},
                )
            )

    def test_false_capability_types(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                _base(
                    mock=False,
                    capability_verification_status="verified",
                    capabilities={"chat": "yes", "tools": False},
                )
            )

    def test_mock_cannot_claim_verified_capabilities(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                _base(
                    mock=True,
                    capability_verification_status="verified",
                    capabilities={"chat": True, "tools": False},
                )
            )

    def test_mock_cannot_claim_tools_true(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                _base(
                    mock=True,
                    capability_verification_status="unverified",
                    capabilities={"chat": False, "tools": True},
                )
            )

    def test_artifact_status_separate_from_capability(self):
        entry = validate_entry_dict(
            _base(
                mock=False,
                artifact_verification_status="verified",
                capability_verification_status="unverified",
                capabilities={"chat": False, "tools": False},
            )
        )
        self.assertEqual(entry.artifact_verification_status, "verified")
        self.assertEqual(entry.capability_verification_status, "unverified")
        # Artefact verified alone must not imply behavioural tools
        self.assertFalse(entry.capabilities.get("tools"))

    def test_unsupported_checksum_algorithm(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                _base(
                    checksum_algorithm="md5",
                    artifact_checksum="d41d8cd98f00b204e9800998ecf8427e",
                )
            )

    def test_wrong_checksum_length(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                _base(
                    checksum_algorithm="sha256",
                    artifact_checksum="abcd",
                )
            )

    def test_nested_secret_field(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                _base(hardware_requirements={"gpu": False, "api_key": "nope"})
            )

    def test_mock_siona_native_forbidden(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(_base(siona_native=True, mock=True))

    def test_unknown_values(self):
        entry = validate_entry_dict(
            _base(
                licence_id="unknown",
                licence_ref="unknown",
                classification="unknown",
            )
        )
        self.assertEqual(entry.licence_id, "unknown")
        self.assertEqual(entry.classification, "unknown")

    def test_duplicate_rejection(self):
        reg = ModelRegistry()
        reg.load_dict(mock_ci_registry_payload())
        with self.assertRaises(RegistryValidationError):
            reg.load_dict(mock_ci_registry_payload())

    def test_same_model_id_distinct_providers(self):
        reg = ModelRegistry()
        reg.load_dict(
            {
                "models": [
                    _base(provider_id="p1", model_id="shared"),
                    _base(provider_id="p2", model_id="shared"),
                ]
            }
        )
        self.assertEqual(len(reg), 2)
        self.assertIsNotNone(reg.get("shared", provider_id="p1"))
        self.assertIsNotNone(reg.get("shared", provider_id="p2"))

    def test_partial_load_rollback(self):
        reg = ModelRegistry()
        reg.load_dict(mock_ci_registry_payload())
        before = len(reg)
        with self.assertRaises(RegistryValidationError):
            reg.load_dict(
                {
                    "models": [
                        _base(provider_id="ok", model_id="new1"),
                        _base(provider_id="bad", model_id="new2", context_window=-5),
                    ]
                }
            )
        self.assertEqual(len(reg), before)
        self.assertIsNone(reg.get("new1", provider_id="ok"))

    def test_malformed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{not-json", encoding="utf-8")
            reg = ModelRegistry()
            with self.assertRaises(RegistryValidationError):
                reg.load_json_file(path)

    def test_secret_field_forbidden(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(_base(api_key="nope"))  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
