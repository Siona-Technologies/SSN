"""
Model registry and provenance contracts (Phase 3A).

Records metadata only. Does not claim ownership of third-party weights.
CI fixtures use clearly labelled mock entries.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


REQUIRED_FIELDS = (
    "provider_id",
    "model_id",
)

OPTIONAL_NULLABLE = (
    "model_family",
    "model_version",
    "runtime",
    "format",
    "quantization",
    "context_window",
    "source",
    "licence_id",
    "licence_ref",
    "checksum_algorithm",
    "artifact_checksum",
    "classification",  # local | remote | unknown
    "hardware_requirements",
    "added_date",
    "verification_status",
    "notes",
    "limitations",
)


class RegistryValidationError(ValueError):
    pass


@dataclass
class ModelRegistryEntry:
    provider_id: str
    model_id: str
    model_family: Optional[str] = None
    model_version: Optional[str] = None
    runtime: Optional[str] = None
    format: Optional[str] = None
    quantization: Optional[str] = None
    context_window: Optional[int] = None
    source: Optional[str] = None
    licence_id: Optional[str] = None
    licence_ref: Optional[str] = None
    checksum_algorithm: Optional[str] = None
    artifact_checksum: Optional[str] = None
    classification: Optional[str] = "unknown"
    hardware_requirements: Optional[Dict[str, Any]] = None
    added_date: Optional[str] = None
    verification_status: Optional[str] = "unverified"
    notes: Optional[str] = None
    limitations: Optional[str] = None
    mock: bool = False
    siona_native: bool = False  # must remain False for third-party open weights

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _unknown_or_str(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        if not s or s.lower() in {"unknown", "null", "none", "n/a"}:
            return None if s.lower() in {"null", "none"} else (s if s else None)
        return s
    return str(value)


def validate_entry_dict(data: Dict[str, Any]) -> ModelRegistryEntry:
    if not isinstance(data, dict):
        raise RegistryValidationError("entry_not_object")
    for key in REQUIRED_FIELDS:
        if not data.get(key) or not str(data.get(key)).strip():
            raise RegistryValidationError(f"missing_required:{key}")

    # Reject fabricated secret-looking fields
    for banned in ("api_key", "master_key", "password", "token", "secret"):
        if banned in data:
            raise RegistryValidationError(f"secret_field_forbidden:{banned}")

    checksum_alg = _unknown_or_str(data.get("checksum_algorithm"))
    checksum_val = _unknown_or_str(data.get("artifact_checksum"))
    if (checksum_alg and not checksum_val) or (checksum_val and not checksum_alg):
        raise RegistryValidationError("checksum_incomplete")

    licence_id = _unknown_or_str(data.get("licence_id"))
    licence_ref = _unknown_or_str(data.get("licence_ref"))
    # Incomplete licence pair is allowed only if both unknown/null
    # If one is fabricated empty string we already normalized.

    ctx = data.get("context_window")
    context_window: Optional[int]
    if ctx is None or ctx == "unknown":
        context_window = None
    else:
        try:
            context_window = int(ctx)
        except Exception as exc:
            raise RegistryValidationError(f"invalid_context_window:{exc}") from exc

    classification = _unknown_or_str(data.get("classification")) or "unknown"
    if classification not in {"local", "remote", "unknown"}:
        raise RegistryValidationError(f"invalid_classification:{classification}")

    hw = data.get("hardware_requirements")
    if hw is not None and not isinstance(hw, dict):
        raise RegistryValidationError("hardware_requirements_not_object")

    if data.get("siona_native") is True and not data.get("mock"):
        # Third-party open weights must not be claimed as SIONA-native.
        raise RegistryValidationError("siona_native_forbidden_for_third_party")

    return ModelRegistryEntry(
        provider_id=str(data["provider_id"]).strip(),
        model_id=str(data["model_id"]).strip(),
        model_family=_unknown_or_str(data.get("model_family")),
        model_version=_unknown_or_str(data.get("model_version")),
        runtime=_unknown_or_str(data.get("runtime")),
        format=_unknown_or_str(data.get("format")),
        quantization=_unknown_or_str(data.get("quantization")),
        context_window=context_window,
        source=_unknown_or_str(data.get("source")),
        licence_id=licence_id,
        licence_ref=licence_ref,
        checksum_algorithm=checksum_alg,
        artifact_checksum=checksum_val,
        classification=classification,
        hardware_requirements=dict(hw) if isinstance(hw, dict) else None,
        added_date=_unknown_or_str(data.get("added_date")),
        verification_status=_unknown_or_str(data.get("verification_status")) or "unverified",
        notes=_unknown_or_str(data.get("notes")),
        limitations=_unknown_or_str(data.get("limitations")),
        mock=bool(data.get("mock", False)),
        siona_native=bool(data.get("siona_native", False)),
    )


class ModelRegistry:
    def __init__(self) -> None:
        self._by_id: Dict[str, ModelRegistryEntry] = {}

    def __len__(self) -> int:
        return len(self._by_id)

    def get(self, model_id: str) -> Optional[ModelRegistryEntry]:
        return self._by_id.get(model_id)

    def list_entries(self) -> List[ModelRegistryEntry]:
        return list(self._by_id.values())

    def add(self, entry: ModelRegistryEntry, *, allow_duplicate: bool = False) -> None:
        if entry.model_id in self._by_id and not allow_duplicate:
            raise RegistryValidationError(f"duplicate_model_id:{entry.model_id}")
        self._by_id[entry.model_id] = entry

    def load_dict(self, payload: Dict[str, Any]) -> None:
        if not isinstance(payload, dict):
            raise RegistryValidationError("registry_not_object")
        models = payload.get("models")
        if models is None:
            raise RegistryValidationError("missing_models")
        if not isinstance(models, list):
            raise RegistryValidationError("models_not_list")
        for i, item in enumerate(models):
            if not isinstance(item, dict):
                raise RegistryValidationError(f"entry_not_object:{i}")
            entry = validate_entry_dict(item)
            self.add(entry)

    def load_json_file(self, path: str | Path) -> None:
        p = Path(path)
        try:
            raw = p.read_text(encoding="utf-8")
        except Exception as exc:
            raise RegistryValidationError(f"unreadable:{exc}") from exc
        try:
            payload = json.loads(raw)
        except Exception as exc:
            raise RegistryValidationError(f"invalid_json:{exc}") from exc
        self.load_dict(payload)

    def to_dict(self) -> Dict[str, Any]:
        return {"models": [e.to_dict() for e in self.list_entries()]}


def load_registry(path: str | Path) -> ModelRegistry:
    reg = ModelRegistry()
    reg.load_json_file(path)
    return reg


def mock_ci_registry_payload() -> Dict[str, Any]:
    """Clearly labelled mock registry for CI — not a real model entry."""
    return {
        "models": [
            {
                "provider_id": "siona-local-open-weight-v1",
                "model_id": "mock-ci-open-weight",
                "model_family": "mock",
                "model_version": "ci-fixture-1",
                "runtime": "mock-http",
                "format": "http-json",
                "quantization": None,
                "context_window": 2048,
                "source": "ci-fixture",
                "licence_id": None,
                "licence_ref": None,
                "checksum_algorithm": None,
                "artifact_checksum": None,
                "classification": "local",
                "hardware_requirements": {"gpu": False, "cpu_ok": True},
                "added_date": "2026-08-05",
                "verification_status": "mock",
                "notes": "CI mock entry only — not a real open-weight model",
                "limitations": "Deterministic/mock validation only (Phase 3A)",
                "mock": True,
                "siona_native": False,
            }
        ]
    }
