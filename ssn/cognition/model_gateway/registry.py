"""
Model registry and provenance contracts (Phase 3A/3B).

Strict schema validation with transactional loading.
CI fixtures use clearly labelled mock entries — never SIONA-native.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

ALLOWED_ROOT_FIELDS: Set[str] = {"models"}

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
    "verification_status",  # legacy alias → artifact_verification_status
    "artifact_verification_status",
    "capability_verification_status",
    "capabilities",
    "notes",
    "limitations",
    "mock",
    "siona_native",
}

ALLOWED_CAPABILITY_FIELDS: Set[str] = {
    "chat",
    "tools",
    "structured_json",
    "streaming",
    "multimodal",
    "context_window",
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
MAX_REGISTRY_FILE_BYTES = 256_000
MAX_REGISTRY_ENTRIES = 32

CANONICAL_REGISTRY_RELATIVE_PATH = "config/model_registry.json"
APPROVED_BASELINE_PROVIDER_ID = "siona-local-open-weight-v1"
APPROVED_BASELINE_MODEL_ID = "Qwen3-1.7B-Q4_K_M"
APPROVED_BASELINE_ARTIFACT_SHA256 = (
    "d2387ca2dbfee2ffabce7120d3770dadca0b293052bc2f0e138fdc940d9bc7b5"
)

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
    artifact_verification_status: Optional[str] = "unverified"
    capability_verification_status: Optional[str] = "unverified"
    verification_status: Optional[str] = "unverified"
    capabilities: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    limitations: Optional[str] = None
    mock: bool = False
    siona_native: bool = False

    def composite_key(self) -> Tuple[str, str]:
        return (self.provider_id, self.model_id)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def canonical_registry_path() -> Path:
    return repo_root() / CANONICAL_REGISTRY_RELATIVE_PATH


def _require_exact_dict(value: Any, *, label: str) -> Dict[str, Any]:
    if type(value) is not dict:
        raise RegistryValidationError(f"{label}_not_object")
    return value


def _require_exact_list(value: Any, *, label: str) -> List[Any]:
    if type(value) is not list:
        raise RegistryValidationError(f"{label}_not_list")
    return value


def _require_exact_bool(value: Any, field: str, *, default: bool = False) -> bool:
    if value is None:
        return default
    if type(value) is not bool:
        raise RegistryValidationError(f"expected_bool:{field}")
    return value


def _require_exact_positive_int(value: Any, field: str) -> int:
    if type(value) is bool:
        raise RegistryValidationError(f"expected_positive_int:{field}")
    if type(value) is not int:
        raise RegistryValidationError(f"expected_positive_int:{field}")
    if value <= 0:
        raise RegistryValidationError(f"{field}_not_positive")
    return value


def _require_finite_number(value: Any, field: str) -> float:
    if type(value) is bool:
        raise RegistryValidationError(f"expected_finite_number:{field}")
    if type(value) not in {int, float}:
        raise RegistryValidationError(f"expected_finite_number:{field}")
    number = float(value)
    if not math.isfinite(number):
        raise RegistryValidationError(f"non_finite_number:{field}")
    return number


def _unknown_or_str(value: Any, *, max_len: int = MAX_STRING) -> Optional[str]:
    if value is None:
        return None
    if type(value) is not str:
        raise RegistryValidationError("expected_string")
    s = value.strip()
    if not s:
        return None
    if s.lower() in {"null", "none"}:
        return None
    if len(s) > max_len:
        raise RegistryValidationError("string_too_long")
    return s


def _reject_secrets_recursive(obj: Any, *, depth: int = 0) -> None:
    if depth > 8:
        raise RegistryValidationError("depth_exceeded")
    if type(obj) is dict:
        for k, v in obj.items():
            key = str(k).lower().replace("-", "_")
            if key in _SECRET_KEYS or key.endswith("_secret") or key.endswith("_password"):
                raise RegistryValidationError(f"secret_field_forbidden:{k}")
            _reject_secrets_recursive(v, depth=depth + 1)
    elif type(obj) is list:
        for item in obj[:64]:
            _reject_secrets_recursive(item, depth=depth + 1)


def _validate_hw(hw: Any, *, depth: int = 0) -> Dict[str, Any]:
    hw = _require_exact_dict(hw, label="hardware_requirements")
    if depth > MAX_HW_DEPTH:
        raise RegistryValidationError("hardware_requirements_depth")
    if len(hw) > MAX_HW_KEYS:
        raise RegistryValidationError("hardware_requirements_too_many_keys")
    out: Dict[str, Any] = {}
    for k, v in hw.items():
        if type(k) is not str:
            raise RegistryValidationError("hardware_requirements_key_not_string")
        key = k[:64]
        if type(v) is dict:
            out[key] = _validate_hw(v, depth=depth + 1)
        elif type(v) is bool:
            out[key] = v
        elif type(v) is int:
            _require_finite_number(v, f"hardware_requirements.{key}")
            out[key] = v
        elif type(v) is float:
            _require_finite_number(v, f"hardware_requirements.{key}")
            out[key] = v
        elif type(v) is str:
            if len(v) > MAX_STRING:
                raise RegistryValidationError("hardware_requirements_string_too_long")
            out[key] = v
        elif v is None:
            out[key] = None
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


def _validate_capabilities(raw: Any) -> Optional[Dict[str, Any]]:
    """Validate explicit behavioural capabilities with exact types."""
    if raw is None:
        return None
    raw = _require_exact_dict(raw, label="capabilities")
    unknown = set(raw.keys()) - ALLOWED_CAPABILITY_FIELDS
    if unknown:
        raise RegistryValidationError(f"unknown_capability_fields:{sorted(unknown)}")
    out: Dict[str, Any] = {
        "chat": False,
        "tools": False,
        "structured_json": False,
        "streaming": False,
        "multimodal": False,
        "context_window": None,
    }
    for key in ("chat", "tools", "structured_json", "streaming", "multimodal"):
        if key not in raw or raw[key] is None:
            continue
        out[key] = _require_exact_bool(raw[key], key)
    if "context_window" in raw and raw["context_window"] is not None:
        out["context_window"] = _require_exact_positive_int(raw["context_window"], "context_window")
    return out


def _parse_registry_json(raw: str) -> Dict[str, Any]:
    def pairs_hook(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
        keys = [k for k, _ in pairs]
        if len(keys) != len(set(keys)):
            raise RegistryValidationError("duplicate_json_keys")
        return dict(pairs)

    try:
        payload = json.loads(raw, object_pairs_hook=pairs_hook)
    except RegistryValidationError:
        raise
    except Exception as exc:
        raise RegistryValidationError(f"invalid_json:{exc}") from exc
    return _require_exact_dict(payload, label="registry")


def parse_registry_bytes(data: bytes) -> Dict[str, Any]:
    if len(data) > MAX_REGISTRY_FILE_BYTES:
        raise RegistryValidationError("registry_file_too_large")
    try:
        raw = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise RegistryValidationError("registry_not_utf8") from exc
    payload = _parse_registry_json(raw)
    unknown_root = set(payload.keys()) - ALLOWED_ROOT_FIELDS
    if unknown_root:
        raise RegistryValidationError(f"unknown_root_fields:{sorted(unknown_root)}")
    return payload


def validate_entry_dict(data: Dict[str, Any]) -> ModelRegistryEntry:
    data = _require_exact_dict(data, label="entry")

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

    if "siona_native" in data:
        if _require_exact_bool(data["siona_native"], "siona_native"):
            raise RegistryValidationError("siona_native_forbidden")

    classification = _unknown_or_str(data.get("classification")) or "unknown"
    if classification not in CLASSIFICATIONS:
        raise RegistryValidationError(f"invalid_classification:{classification}")

    artifact_status = (
        _unknown_or_str(data.get("artifact_verification_status"))
        or _unknown_or_str(data.get("verification_status"))
        or "unverified"
    )
    if artifact_status not in VERIFICATION_STATUSES:
        raise RegistryValidationError(f"invalid_artifact_verification_status:{artifact_status}")

    capability_status = _unknown_or_str(data.get("capability_verification_status")) or "unverified"
    if capability_status not in VERIFICATION_STATUSES:
        raise RegistryValidationError(f"invalid_capability_verification_status:{capability_status}")

    capabilities = _validate_capabilities(data.get("capabilities"))

    is_mock = _require_exact_bool(data.get("mock"), "mock") if "mock" in data else False
    if is_mock and capability_status == "verified":
        raise RegistryValidationError("mock_cannot_claim_verified_capabilities")
    if is_mock and capabilities:
        if any(
            capabilities.get(k) is True
            for k in ("tools", "structured_json", "streaming", "multimodal")
        ):
            raise RegistryValidationError("mock_cannot_claim_real_model_capabilities")

    if capability_status == "verified" and capabilities is None:
        raise RegistryValidationError("verified_capabilities_require_capabilities_object")

    ctx = data.get("context_window")
    context_window: Optional[int]
    if ctx is None or (type(ctx) is str and ctx.strip().lower() in {"unknown", "null", "none", ""}):
        context_window = None
    else:
        context_window = _require_exact_positive_int(ctx, "context_window")

    licence_id = _unknown_or_str(data.get("licence_id"))
    licence_ref = _unknown_or_str(data.get("licence_ref"))
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
        artifact_verification_status=artifact_status,
        capability_verification_status=capability_status,
        verification_status=artifact_status,
        capabilities=capabilities,
        notes=notes,
        limitations=limitations,
        mock=is_mock,
        siona_native=False,
    )


class ModelRegistry:
    def __init__(self) -> None:
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
        """Transactional load: validate all records first, then commit."""
        payload = _require_exact_dict(payload, label="registry")
        unknown_root = set(payload.keys()) - ALLOWED_ROOT_FIELDS
        if unknown_root:
            raise RegistryValidationError(f"unknown_root_fields:{sorted(unknown_root)}")
        models = payload.get("models")
        if models is None:
            raise RegistryValidationError("missing_models")
        models = _require_exact_list(models, label="models")
        if len(models) > MAX_REGISTRY_ENTRIES:
            raise RegistryValidationError("too_many_registry_entries")

        pending: List[ModelRegistryEntry] = []
        seen: Set[Tuple[str, str]] = set()
        for i, item in enumerate(models):
            if type(item) is not dict:
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
            data = p.read_bytes()
        except Exception as exc:
            raise RegistryValidationError(f"unreadable:{exc}") from exc
        payload = parse_registry_bytes(data)
        self.load_dict(payload)

    def to_dict(self) -> Dict[str, Any]:
        return {"models": [e.to_dict() for e in self.list_entries()]}


def load_registry(path: str | Path) -> ModelRegistry:
    reg = ModelRegistry()
    reg.load_json_file(path)
    return reg


def lookup_registry_entry(
    registry: ModelRegistry,
    *,
    provider_id: str,
    model_id: str,
) -> ModelRegistryEntry:
    entry = registry.get(model_id, provider_id=provider_id)
    if entry is None:
        raise RegistryValidationError("registry_entry_not_found")
    return entry


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
                "artifact_verification_status": "mock",
                "capability_verification_status": "unverified",
                "capabilities": {
                    "chat": False,
                    "tools": False,
                    "structured_json": False,
                    "streaming": False,
                    "multimodal": False,
                    "context_window": None,
                },
                "notes": "CI mock entry only — not a real open-weight model",
                "limitations": "Deterministic/mock validation only (Phase 3A)",
                "mock": True,
                "siona_native": False,
            }
        ]
    }
