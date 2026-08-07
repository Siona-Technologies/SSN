"""EXP-3B-012 — model registry activation review tests."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("SSN_OFFLINE", "1")

from ssn.cognition.model_gateway.local_provider import (
    LocalOpenWeightProvider,
    LocalProviderError,
    build_local_provider_from_env,
    load_bound_registry_entry,
)
from ssn.cognition.model_gateway.mock_local_server import MockLocalModelServer
from ssn.cognition.model_gateway.registry import (
    APPROVED_BASELINE_ARTIFACT_SHA256,
    APPROVED_BASELINE_MODEL_ID,
    APPROVED_BASELINE_PROVIDER_ID,
    MAX_REGISTRY_FILE_BYTES,
    ModelRegistry,
    RegistryValidationError,
    canonical_registry_path,
    mock_ci_registry_payload,
    parse_registry_bytes,
    validate_entry_dict,
)
from ssn.core.llm_providers import LocalDummyLLMProvider, get_default_provider_from_env


def _approved_entry(**overrides):
    data = {
        "provider_id": APPROVED_BASELINE_PROVIDER_ID,
        "model_id": APPROVED_BASELINE_MODEL_ID,
        "model_family": "Qwen3",
        "model_version": "1.7B",
        "runtime": "llama.cpp b9968",
        "format": "GGUF",
        "quantization": "Q4_K_M",
        "context_window": 4096,
        "source": "ggml-org/Qwen3-1.7B-GGUF revision daeb8e2d528a760970442092f6bf1e55c3b659eb",
        "licence_id": "Apache-2.0",
        "licence_ref": "ggml-org/Qwen3-1.7B-GGUF@daeb8e2d528a760970442092f6bf1e55c3b659eb",
        "checksum_algorithm": "sha256",
        "artifact_checksum": APPROVED_BASELINE_ARTIFACT_SHA256,
        "classification": "local",
        "artifact_verification_status": "verified",
        "capability_verification_status": "verified",
        "capabilities": {
            "chat": True,
            "tools": False,
            "structured_json": False,
            "streaming": False,
            "multimodal": False,
            "context_window": 4096,
        },
        "mock": False,
        "siona_native": False,
    }
    data.update(overrides)
    return data


class TestCanonicalRegistryManifest(unittest.TestCase):
    def test_canonical_manifest_validates(self):
        path = canonical_registry_path()
        self.assertTrue(path.is_file(), msg=str(path))
        reg = ModelRegistry()
        reg.load_json_file(path)
        self.assertEqual(len(reg), 1)
        entry = reg.get(APPROVED_BASELINE_MODEL_ID, provider_id=APPROVED_BASELINE_PROVIDER_ID)
        self.assertIsNotNone(entry)
        self.assertFalse(entry.mock)
        self.assertFalse(entry.siona_native)
        self.assertEqual(entry.artifact_checksum, APPROVED_BASELINE_ARTIFACT_SHA256)
        self.assertEqual(entry.capability_verification_status, "verified")
        caps = entry.capabilities or {}
        self.assertTrue(caps.get("chat"))
        self.assertFalse(caps.get("tools"))
        self.assertFalse(caps.get("structured_json"))
        self.assertFalse(caps.get("streaming"))
        self.assertFalse(caps.get("multimodal"))
        self.assertEqual(caps.get("context_window"), 4096)


class TestStrictRegistryParsing(unittest.TestCase):
    def test_string_boolean_rejected(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(_approved_entry(mock="false"))

    def test_bool_as_int_rejected(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                _approved_entry(
                    capabilities={
                        "chat": 1,
                        "tools": False,
                        "structured_json": False,
                        "streaming": False,
                        "multimodal": False,
                        "context_window": 4096,
                    }
                )
            )

    def test_numeric_string_context_rejected(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(_approved_entry(context_window="4096"))
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                _approved_entry(
                    capabilities={
                        "chat": True,
                        "tools": False,
                        "structured_json": False,
                        "streaming": False,
                        "multimodal": False,
                        "context_window": "4096",
                    }
                )
            )

    def test_non_finite_hardware_rejected(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                _approved_entry(hardware_requirements={"vram_gb": float("inf")})
            )

    def test_duplicate_json_keys_rejected(self):
        raw = '{"models": [{"provider_id": "p", "model_id": "m", "mock": false, "mock": true}]}'
        with self.assertRaises(RegistryValidationError) as ctx:
            parse_registry_bytes(raw.encode("utf-8"))
        self.assertIn("duplicate_json_keys", str(ctx.exception))

    def test_oversized_registry_rejected(self):
        blob = b"x" * (MAX_REGISTRY_FILE_BYTES + 1)
        with self.assertRaises(RegistryValidationError):
            parse_registry_bytes(blob)

    def test_mock_pretending_verified_rejected(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                _approved_entry(mock=True, capability_verification_status="verified")
            )

    def test_siona_native_true_rejected(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(_approved_entry(siona_native=True))

    def test_verified_without_capabilities_rejected(self):
        with self.assertRaises(RegistryValidationError):
            validate_entry_dict(
                _approved_entry(capability_verification_status="verified", capabilities=None)
            )


class TestRegistryProviderBinding(unittest.TestCase):
    def _write_registry(self, tmp: Path, models: list) -> Path:
        path = tmp / "registry.json"
        path.write_text(json.dumps({"models": models}), encoding="utf-8")
        return path

    def test_exact_binding_success(self):
        server = MockLocalModelServer(mode="ok").start()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                reg_path = self._write_registry(Path(tmp), [_approved_entry()])
                with mock.patch.dict(
                    os.environ,
                    {
                        "SSN_MODEL_PROVIDER": "local",
                        "SSN_LOCAL_MODEL_ENDPOINT": server.generate_url,
                        "SSN_LOCAL_MODEL_ID": APPROVED_BASELINE_MODEL_ID,
                        "SSN_MODEL_REGISTRY_PATH": str(reg_path),
                    },
                    clear=False,
                ):
                    provider = build_local_provider_from_env()
                    self.assertIsNotNone(provider)
                    caps = provider.capabilities()
                    self.assertTrue(caps.chat)
                    self.assertFalse(caps.tools)
                    self.assertFalse(caps.structured_json)
                    self.assertFalse(caps.streaming)
                    self.assertFalse(caps.multimodal)
                    self.assertEqual(caps.context_window, 4096)
                    self.assertTrue(caps.metadata.get("model_registry_entry_bound"))
                    self.assertEqual(
                        caps.metadata.get("model_registry_capability_status"), "verified"
                    )
                    self.assertFalse(caps.metadata.get("trained_siona_native"))
                    self.assertTrue(caps.metadata.get("open_weight"))
        finally:
            server.stop()

    def test_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg_path = self._write_registry(Path(tmp), [_approved_entry()])
            with mock.patch.dict(
                os.environ,
                {
                    "SSN_MODEL_PROVIDER": "local",
                    "SSN_LOCAL_MODEL_ID": "wrong-model-id",
                    "SSN_MODEL_REGISTRY_PATH": str(reg_path),
                },
                clear=False,
            ):
                with self.assertRaises(LocalProviderError) as ctx:
                    load_bound_registry_entry()
                self.assertIn("mismatch", str(ctx.exception))

    def test_wrong_provider_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg_path = self._write_registry(
                Path(tmp),
                [_approved_entry(provider_id="other-provider")],
            )
            with mock.patch.dict(
                os.environ,
                {
                    "SSN_MODEL_PROVIDER": "local",
                    "SSN_LOCAL_MODEL_ID": APPROVED_BASELINE_MODEL_ID,
                    "SSN_MODEL_REGISTRY_PATH": str(reg_path),
                },
                clear=False,
            ):
                with self.assertRaises(LocalProviderError):
                    load_bound_registry_entry()

    def test_default_dummy_never_loads_registry(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            os.environ.pop("SSN_MODEL_PROVIDER", None)
            os.environ.pop("SSN_LLM_PROVIDER", None)
            provider = get_default_provider_from_env()
            self.assertIsInstance(provider, LocalDummyLLMProvider)

    def test_registry_mismatch_gateway_fails_closed_to_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            reg_path = self._write_registry(Path(tmp), [_approved_entry()])
            with mock.patch.dict(
                os.environ,
                {
                    "SSN_LLM_PROVIDER": "local",
                    "SSN_LOCAL_MODEL_ID": "wrong-model-id",
                    "SSN_MODEL_REGISTRY_PATH": str(reg_path),
                },
                clear=False,
            ):
                provider = get_default_provider_from_env()
                self.assertEqual(provider.name, "ssn-gateway-deterministic-v1")

    def test_registry_entry_cannot_grant_tool_authority(self):
        entry = validate_entry_dict(_approved_entry())
        provider = LocalOpenWeightProvider(
            endpoint="http://127.0.0.1:9/g",
            model_id=APPROVED_BASELINE_MODEL_ID,
            registry_entry=entry,
        )
        caps = provider.capabilities()
        self.assertFalse(caps.tools)

    def test_malformed_registry_cannot_grant_capability(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.json"
            path.write_text("{not-json", encoding="utf-8")
            with mock.patch.dict(
                os.environ,
                {
                    "SSN_MODEL_PROVIDER": "local",
                    "SSN_LOCAL_MODEL_ID": APPROVED_BASELINE_MODEL_ID,
                    "SSN_MODEL_REGISTRY_PATH": str(path),
                },
                clear=False,
            ):
                with self.assertRaises(LocalProviderError):
                    load_bound_registry_entry()


class TestRegistryLoadIsolation(unittest.TestCase):
    def test_no_subprocess_or_network_during_parse(self):
        import subprocess

        calls = {"popen": 0, "urlopen": 0}

        original_popen = subprocess.Popen

        def track_popen(*args, **kwargs):
            calls["popen"] += 1
            return original_popen(*args, **kwargs)

        with mock.patch("subprocess.Popen", side_effect=track_popen):
            with mock.patch("urllib.request.urlopen", side_effect=AssertionError("network")):
                reg = ModelRegistry()
                reg.load_json_file(canonical_registry_path())
                self.assertEqual(len(reg), 1)
        self.assertEqual(calls["popen"], 0)


if __name__ == "__main__":
    unittest.main()
