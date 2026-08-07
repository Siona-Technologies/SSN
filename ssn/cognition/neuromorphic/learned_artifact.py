"""Strict loader for EXP-4-003 learned neuromorphic candidate artifacts."""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence, Tuple

APPROVED_ARTIFACT_SHA256 = (
    "dfc548e4247ad740ffc2c62c68fb9ad0f9af01bcaecbdb41527aeeb275f4fdcc"
)
APPROVED_ARTIFACT_RELATIVE_PATH = Path("artifacts/neuromorphic/phase4b-lif-final-membrane-v1.json")
MAX_ARTIFACT_BYTES = 256 * 1024

PROVIDER_TARGET = "siona-neuro-learned-lif-v1"
ARTIFACT_TYPE = "SIONA_LEARNED_NEUROMORPHIC_CANDIDATE"
TASK_ID = "phase4a-temporal-salience-v1"
ARCHITECTURE_ID = "phase4b-lif-final-membrane-v1"
TRAINING_EXPERIMENT = "EXP-4-003"
TRAINING_SEED = 42007

APPROVED_DATASET_FINGERPRINTS = {
    "train": "e124d6b5858399956f7b52f1fc6e342e9d2833704b44710315d57844c43805bd",
    "validation": "cfd32c4b9b2684dc10f21e9b28d169807c42ae54e7968d5080a676d602929285",
    "test": "34d93878277a0b6afae880c02a3b2d878fbc142a1cfee77b51985eebbf7f4116",
}

APPROVED_LIF = {
    "beta": 0.9,
    "threshold": 1.0,
    "reset_mechanism": "subtract",
    "surrogate": "fast_sigmoid",
    "surrogate_slope": 25.0,
    "learn_beta": False,
    "learn_threshold": False,
}

WEIGHT_SHAPES = {
    "fc1.weight": (16, 8),
    "fc1.bias": (16,),
    "fc2.weight": (2, 16),
    "fc2.bias": (2,),
}

ALLOWED_ROOT_KEYS = frozenset(
    {
        "schema_version",
        "artifact_type",
        "provider_target",
        "task_id",
        "architecture_id",
        "training_experiment",
        "backend",
        "dataset_fingerprints",
        "training_seed",
        "lif",
        "weights",
        "accepted_metrics",
        "tool_authority",
        "physical_actuation_authority",
    }
)


class LearnedNeuromorphicArtifactError(ValueError):
    """Fail-closed validation error for learned neuromorphic artifacts."""


def _reject_duplicate_keys(pairs: List[Tuple[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for key, value in pairs:
        if key in out:
            raise LearnedNeuromorphicArtifactError(f"duplicate_json_key:{key}")
        out[key] = value
    return out


def _is_finite_number(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _require_exact(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise LearnedNeuromorphicArtifactError(f"{label}_mismatch")


def _require_false(value: Any, label: str) -> None:
    if value is not False:
        raise LearnedNeuromorphicArtifactError(f"{label}_must_be_false")


def _validate_matrix(name: str, value: Any, shape: Tuple[int, ...]) -> Tuple[Tuple[float, ...], ...]:
    if not isinstance(value, list):
        raise LearnedNeuromorphicArtifactError(f"{name}_not_list")
    if len(shape) == 1:
        if len(value) != shape[0]:
            raise LearnedNeuromorphicArtifactError(f"{name}_shape")
        row: List[float] = []
        for item in value:
            if not _is_finite_number(item):
                raise LearnedNeuromorphicArtifactError(f"{name}_non_finite_or_non_numeric")
            row.append(float(item))
        return (tuple(row),)
    if len(shape) != 2:
        raise LearnedNeuromorphicArtifactError(f"{name}_unsupported_shape")
    rows, cols = shape
    if len(value) != rows:
        raise LearnedNeuromorphicArtifactError(f"{name}_shape")
    matrix: List[Tuple[float, ...]] = []
    for row in value:
        if not isinstance(row, list) or len(row) != cols:
            raise LearnedNeuromorphicArtifactError(f"{name}_shape")
        parsed: List[float] = []
        for item in row:
            if not _is_finite_number(item):
                raise LearnedNeuromorphicArtifactError(f"{name}_non_finite_or_non_numeric")
            parsed.append(float(item))
        matrix.append(tuple(parsed))
    return tuple(matrix)


def _validate_lif(lif: Any) -> Dict[str, Any]:
    if not isinstance(lif, dict):
        raise LearnedNeuromorphicArtifactError("lif_not_object")
    if set(lif.keys()) != set(APPROVED_LIF.keys()):
        raise LearnedNeuromorphicArtifactError("lif_keys_mismatch")
    for key, expected in APPROVED_LIF.items():
        actual = lif[key]
        if isinstance(expected, bool):
            if actual is not expected:
                raise LearnedNeuromorphicArtifactError(f"lif_{key}_mismatch")
        elif isinstance(expected, float):
            if isinstance(actual, bool) or not isinstance(actual, (int, float)):
                raise LearnedNeuromorphicArtifactError(f"lif_{key}_mismatch")
            if float(actual) != expected:
                raise LearnedNeuromorphicArtifactError(f"lif_{key}_mismatch")
        elif actual != expected:
            raise LearnedNeuromorphicArtifactError(f"lif_{key}_mismatch")
    return dict(APPROVED_LIF)


def _validate_fingerprints(value: Any) -> Dict[str, str]:
    if not isinstance(value, dict):
        raise LearnedNeuromorphicArtifactError("dataset_fingerprints_not_object")
    if set(value.keys()) != set(APPROVED_DATASET_FINGERPRINTS.keys()):
        raise LearnedNeuromorphicArtifactError("dataset_fingerprints_keys_mismatch")
    for key, expected in APPROVED_DATASET_FINGERPRINTS.items():
        if value.get(key) != expected:
            raise LearnedNeuromorphicArtifactError(f"dataset_fingerprint_{key}_mismatch")
    return dict(APPROVED_DATASET_FINGERPRINTS)


def validate_artifact_mapping(payload: Mapping[str, Any], *, sha256_hex: str) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        raise LearnedNeuromorphicArtifactError("root_not_object")
    unknown = set(payload.keys()) - ALLOWED_ROOT_KEYS
    if unknown:
        raise LearnedNeuromorphicArtifactError(f"unknown_root_fields:{sorted(unknown)[0]}")
    missing = ALLOWED_ROOT_KEYS - set(payload.keys())
    if missing:
        raise LearnedNeuromorphicArtifactError(f"missing_root_fields:{sorted(missing)[0]}")

    if sha256_hex != APPROVED_ARTIFACT_SHA256:
        raise LearnedNeuromorphicArtifactError("artifact_sha256_mismatch")

    schema_version = payload.get("schema_version")
    if isinstance(schema_version, bool) or schema_version != 1:
        raise LearnedNeuromorphicArtifactError("schema_version_mismatch")
    _require_exact(payload.get("artifact_type"), ARTIFACT_TYPE, "artifact_type")
    _require_exact(payload.get("provider_target"), PROVIDER_TARGET, "provider_target")
    _require_exact(payload.get("task_id"), TASK_ID, "task_id")
    _require_exact(payload.get("architecture_id"), ARCHITECTURE_ID, "architecture_id")
    _require_exact(payload.get("training_experiment"), TRAINING_EXPERIMENT, "training_experiment")
    training_seed = payload.get("training_seed")
    if isinstance(training_seed, bool) or training_seed != TRAINING_SEED:
        raise LearnedNeuromorphicArtifactError("training_seed_mismatch")
    _require_false(payload.get("tool_authority"), "tool_authority")
    _require_false(payload.get("physical_actuation_authority"), "physical_actuation_authority")

    fingerprints = _validate_fingerprints(payload.get("dataset_fingerprints"))
    lif = _validate_lif(payload.get("lif"))

    weights_raw = payload.get("weights")
    if not isinstance(weights_raw, dict):
        raise LearnedNeuromorphicArtifactError("weights_not_object")
    if set(weights_raw.keys()) != set(WEIGHT_SHAPES.keys()):
        raise LearnedNeuromorphicArtifactError("weights_keys_mismatch")
    weights: Dict[str, Tuple[Tuple[float, ...], ...]] = {}
    for name, shape in WEIGHT_SHAPES.items():
        parsed = _validate_matrix(name, weights_raw[name], shape)
        if len(shape) == 1:
            weights[name] = parsed[0]  # type: ignore[assignment]
        else:
            weights[name] = parsed

    backend = payload.get("backend")
    if not isinstance(backend, dict):
        raise LearnedNeuromorphicArtifactError("backend_not_object")
    accepted = payload.get("accepted_metrics")
    if not isinstance(accepted, dict):
        raise LearnedNeuromorphicArtifactError("accepted_metrics_not_object")

    return {
        "schema_version": 1,
        "artifact_type": ARTIFACT_TYPE,
        "provider_target": PROVIDER_TARGET,
        "task_id": TASK_ID,
        "architecture_id": ARCHITECTURE_ID,
        "training_experiment": TRAINING_EXPERIMENT,
        "training_seed": TRAINING_SEED,
        "tool_authority": False,
        "physical_actuation_authority": False,
        "dataset_fingerprints": fingerprints,
        "lif": lif,
        "weights": {
            "fc1.weight": weights["fc1.weight"],
            "fc1.bias": weights["fc1.bias"],
            "fc2.weight": weights["fc2.weight"],
            "fc2.bias": weights["fc2.bias"],
        },
        "backend": dict(backend),
        "accepted_metrics": dict(accepted),
        "sha256": sha256_hex,
    }


def load_learned_artifact(
    path: Path | str | None = None,
    *,
    expected_sha256: str = APPROVED_ARTIFACT_SHA256,
) -> Dict[str, Any]:
    artifact_path = Path(path) if path is not None else _default_artifact_path()
    raw = artifact_path.read_bytes()
    if len(raw) > MAX_ARTIFACT_BYTES:
        raise LearnedNeuromorphicArtifactError("artifact_too_large")
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha256:
        raise LearnedNeuromorphicArtifactError("artifact_sha256_mismatch")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise LearnedNeuromorphicArtifactError("artifact_not_utf8") from exc
    try:
        payload = json.loads(text, object_pairs_hook=_reject_duplicate_keys)
    except LearnedNeuromorphicArtifactError:
        raise
    except json.JSONDecodeError as exc:
        raise LearnedNeuromorphicArtifactError("artifact_json_invalid") from exc
    if not isinstance(payload, dict):
        raise LearnedNeuromorphicArtifactError("root_not_object")
    return validate_artifact_mapping(payload, sha256_hex=digest)


def _default_artifact_path() -> Path:
    # Repository root: ssn/cognition/neuromorphic/../../..
    root = Path(__file__).resolve().parents[3]
    return root / APPROVED_ARTIFACT_RELATIVE_PATH


def matrix_shape(matrix: Sequence[Sequence[float]] | Sequence[float]) -> Tuple[int, ...]:
    if not matrix:
        return (0,)
    first = matrix[0]
    if isinstance(first, (list, tuple)):
        return (len(matrix), len(first))  # type: ignore[arg-type]
    return (len(matrix),)
