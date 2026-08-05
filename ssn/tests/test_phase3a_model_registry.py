"""Phase 3A — model registry provenance tests."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from ssn.cognition.model_gateway.registry import (
    ModelRegistry,
    RegistryValidationError,
    mock_ci_registry_payload,
    validate_entry_dict,
)


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
        entry = validate_entry_dict(
            {
                "provider_id": "p",
                "model_id": "m1",
                "mock": True,
                "siona_native": False,
            }
        )
        self.assertIsNone(entry.licence_id)
        self.assertIsNone(entry.artifact_checksum)

    def test_missing_required_fields(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict({"provider_id": "p"})
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict({"model_id": "m"})

    def test_invalid_checksum_structure(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                {
                    "provider_id": "p",
                    "model_id": "m",
                    "checksum_algorithm": "sha256",
                    "artifact_checksum": None,
                    "mock": True,
                }
            )

    def test_unknown_values(self):
        entry = validate_entry_dict(
            {
                "provider_id": "p",
                "model_id": "m",
                "licence_id": "unknown",
                "classification": "unknown",
                "mock": True,
            }
        )
        self.assertEqual(entry.licence_id, "unknown")
        self.assertEqual(entry.classification, "unknown")

    def test_duplicate_model_id(self):
        reg = ModelRegistry()
        reg.load_dict(mock_ci_registry_payload())
        with self.assertRaises(RegistryValidationError):
            reg.load_dict(mock_ci_registry_payload())

    def test_malformed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{not-json", encoding="utf-8")
            reg = ModelRegistry()
            with self.assertRaises(RegistryValidationError):
                reg.load_json_file(path)

    def test_secret_field_forbidden(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                {
                    "provider_id": "p",
                    "model_id": "m",
                    "api_key": "nope",
                    "mock": True,
                }
            )

    def test_siona_native_forbidden_for_third_party(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                {
                    "provider_id": "p",
                    "model_id": "m",
                    "siona_native": True,
                    "mock": False,
                }
            )


if __name__ == "__main__":
    unittest.main()
