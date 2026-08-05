"""
Model registry and provenance contracts (Phase 3A).

Strict schema validation with transactional loading.
CI fixtures use clearly labelled mock entries — never SIONA-native.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ALLOWED_FIELDS: Set[str] = {
    "provider_id",
    "model_id",
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
    "classification",
    "hardware_requirements",
    "added_date",
    "verification_status",
    "notes",
    "limitations",
    "mock",
    "siona_native",
}

CLASSIFICATIONS = frozenset({"local", "remote", "unknown"})
VERIFICATION_STATUSES = frozenset({"unverified", "verified", "mock", "rejected", "unknown"})
CHECKSUM_ALGORITHMS = {
    "sha256": 64,
    "sha512": 128,
    "sha1": 40,
    "blake2b": 128,
}

ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
MAX_STRING = 2_048
MAX_NOTES = 4_096
MAX_HW_KEYS = 16
MAX_HW_DEPTH = 3

_SECRET_KEYS = frozenset(
    {
        "api_key",
        "master_key",
        "password",
        "token",
        "secret",
        "access_token",
        "refresh_token",
        "authorization",
        "private_key",
        "client_secret",
    }
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
    siona_native: bool = False

    def composite_key(self) -> Tuple[str, str]:
        return (self.provider_id, self.model_id)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _unknown_or_str(value: Any, *, max_len: int = MAX_STRING) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if s.lower() in {"null", "none"}:
            return None
        if len(s) > max_len:
            raise RegistryValidationError("string_too_long")
        return s
    raise RegistryValidationError("expected_string")


def _reject_secrets_recursive(obj: Any, *, depth: int = 0) -> None:
    if depth > 8:
        raise RegistryValidationError("depth_exceeded")
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = str(k).lower().replace("-", "_")
            if key in _SECRET_KEYS or key.endswith("_secret") or key.endswith("_password"):
                raise RegistryValidationError(f"secret_field_forbidden:{k}")
            _reject_secrets_recursive(v, depth=depth + 1)
    elif isinstance(obj, list):
        for item in obj[:64]:
            _reject_secrets_recursive(item, depth=depth + 1)


def _validate_hw(hw: Any, *, depth: int = 0) -> Dict[str, Any]:
    if not isinstance(hw, dict):
        raise RegistryValidationError("hardware_requirements_not_object")
    if depth > MAX_HW_DEPTH:
        raise RegistryValidationError("hardware_requirements_depth")
    if len(hw) > MAX_HW_KEYS:
        raise RegistryValidationError("hardware_requirements_too_many_keys")
    out: Dict[str, Any] = {}
    for k, v in hw.items():
        key = str(k)[:64]
        if isinstance(v, dict):
            out[key] = _validate_hw(v, depth=depth + 1)
        elif isinstance(v, (str, int, float, bool)) or v is None:
            if isinstance(v, str) and len(v) > MAX_STRING:
                raise RegistryValidationError("hardware_requirements_string_too_long")
            out[key] = v
        else:
            raise RegistryValidationError("hardware_requirements_invalid_value")
    return out


def _validate_added_date(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    s = value.strip()
    if not s or s.lower() == "unknown":
        return s if s.lower() == "unknown" else None
    try:
        if "T" in s:
            datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            date.fromisoformat(s)
    except Exception as exc:
        raise RegistryValidationError(f"invalid_added_date:{exc}") from exc
    return s


def validate_entry_dict(data: Dict[str, Any]) -> ModelRegistryEntry:
    if not isinstance(data, dict):
        raise RegistryValidationError("entry_not_object")

    unknown = set(data.keys()) - ALLOWED_FIELDS
    if unknown:
        raise RegistryValidationError(f"unknown_fields:{sorted(unknown)}")

    _reject_secrets_recursive(data)

    provider_id = _unknown_or_str(data.get("provider_id"))
    model_id = _unknown_or_str(data.get("model_id"))
    if not provider_id or not ID_RE.match(provider_id):
        raise RegistryValidationError("invalid_provider_id")
    if not model_id or not ID_RE.match(model_id):
        raise RegistryValidationError("invalid_model_id")

    # siona_native forbidden for all Phase 3A entries including mocks
    if data.get("siona_native") is True:
        raise RegistryValidationError("siona_native_forbidden")

    classification = _unknown_or_str(data.get("classification")) or "unknown"
    if classification not in CLASSIFICATIONS:
        raise RegistryValidationError(f"invalid_classification:{classification}")

    verification_status = _unknown_or_str(data.get("verification_status")) or "unverified"
    if verification_status not in VERIFICATION_STATUSES:
        raise RegistryValidationError(f"invalid_verification_status:{verification_status}")

    ctx = data.get("context_window")
    context_window: Optional[int]
    if ctx is None or (isinstance(ctx, str) and ctx.strip().lower() in {"unknown", "null", "none", ""}):
        context_window = None
    else:
        try:
            context_window = int(ctx)
        except Exception as exc:
            raise RegistryValidationError(f"invalid_context_window:{exc}") from exc
        if context_window <= 0:
            raise RegistryValidationError("context_window_not_positive")

    licence_id = _unknown_or_str(data.get("licence_id"))
    licence_ref = _unknown_or_str(data.get("licence_ref"))
    # Treat literal "unknown" as present unknown marker — pair rule:
    # both present (including unknown) or both null.
    lic_present = licence_id is not None
    ref_present = licence_ref is not None
    if lic_present != ref_present:
        raise RegistryValidationError("licence_pair_incomplete")

    checksum_alg = _unknown_or_str(data.get("checksum_algorithm"))
    checksum_val = _unknown_or_str(data.get("artifact_checksum"))
    if (checksum_alg is None) != (checksum_val is None):
        raise RegistryValidationError("checksum_incomplete")
    if checksum_alg is not None:
        alg = checksum_alg.lower()
        if alg not in CHECKSUM_ALGORITHMS:
            raise RegistryValidationError(f"unsupported_checksum_algorithm:{checksum_alg}")
        expected = CHECKSUM_ALGORITHMS[alg]
        val = (checksum_val or "").lower()
        if not re.fullmatch(r"[0-9a-f]+", val):
            raise RegistryValidationError("checksum_encoding_invalid")
        if len(val) != expected:
            raise RegistryValidationError(f"checksum_length_invalid:{len(val)}!={expected}")
        checksum_alg = alg
        checksum_val = val

    hw = data.get("hardware_requirements")
    hardware = _validate_hw(hw) if hw is not None else None

    notes = _unknown_or_str(data.get("notes"), max_len=MAX_NOTES)
    limitations = _unknown_or_str(data.get("limitations"), max_len=MAX_NOTES)
    added_date = _validate_added_date(_unknown_or_str(data.get("added_date")))

    return ModelRegistryEntry(
        provider_id=provider_id,
        model_id=model_id,
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
        hardware_requirements=hardware,
        added_date=added_date,
        verification_status=verification_status,
        notes=notes,
        limitations=limitations,
        mock=bool(data.get("mock", False)),
        siona_native=False,
    )


class ModelRegistry:
    def __init__(self) -> None:
        # Composite key: (provider_id, model_id)
        self._by_key: Dict[Tuple[str, str], ModelRegistryEntry] = {}

    def __len__(self) -> int:
        return len(self._by_key)

    def get(self, model_id: str, *, provider_id: Optional[str] = None) -> Optional[ModelRegistryEntry]:
        if provider_id:
            return self._by_key.get((provider_id, model_id))
        matches = [e for (p, m), e in self._by_key.items() if m == model_id]
        if len(matches) == 1:
            return matches[0]
        if not matches:
            return None
        raise RegistryValidationError(f"ambiguous_model_id:{model_id}")

    def list_entries(self) -> List[ModelRegistryEntry]:
        return list(self._by_key.values())

    def add(self, entry: ModelRegistryEntry, *, allow_duplicate: bool = False) -> None:
        key = entry.composite_key()
        if key in self._by_key and not allow_duplicate:
            raise RegistryValidationError(f"duplicate_model:{key[0]}/{key[1]}")
        self._by_key[key] = entry

    def load_dict(self, payload: Dict[str, Any]) -> None:
        """
        Transactional load: validate all records and duplicates first,
        then commit. On failure the existing registry is unchanged.
        """
        if not isinstance(payload, dict):
            raise RegistryValidationError("registry_not_object")
        models = payload.get("models")
        if models is None:
            raise RegistryValidationError("missing_models")
        if not isinstance(models, list):
            raise RegistryValidationError("models_not_list")

        pending: List[ModelRegistryEntry] = []
        seen: Set[Tuple[str, str]] = set()
        for i, item in enumerate(models):
            if not isinstance(item, dict):
                raise RegistryValidationError(f"entry_not_object:{i}")
            entry = validate_entry_dict(item)
            key = entry.composite_key()
            if key in seen or key in self._by_key:
                raise RegistryValidationError(f"duplicate_model:{key[0]}/{key[1]}")
            seen.add(key)
            pending.append(entry)

        for entry in pending:
            self._by_key[entry.composite_key()] = entry

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
