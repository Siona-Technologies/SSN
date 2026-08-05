"""
Centralized runtime-data path resolution.

Default (normal users): repository-relative ``ssn/data`` and ``.ssn_state``.
Tests/smoke/CI: set ``SSN_RUNTIME_DATA_DIR`` to an isolated temporary directory.

Do not silently redirect permanent user data unless the env var is set.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional


ENV_RUNTIME_DATA_DIR = "SSN_RUNTIME_DATA_DIR"
ENV_STATE_DIR = "SSN_STATE_DIR"
ENV_EVAL_OUTPUT_DIR = "SSN_EVAL_OUTPUT_DIR"

_DEFAULT_DATA_REL = Path("ssn") / "data"
_DEFAULT_STATE_REL = Path(".ssn_state")
_DEFAULT_EVAL_REL = Path("artifacts") / "eval"


def _repo_root() -> Path:
    # ssn/runtime/paths.py → parents[2] = repo root
    return Path(__file__).resolve().parents[2]


def get_runtime_data_dir() -> Path:
    """
    Root directory for durable JSON runtime files (world, identity, memory, etc.).

    Precedence:
      1. SSN_RUNTIME_DATA_DIR (absolute or relative to cwd)
      2. <repo>/ssn/data
    """
    override = (os.getenv(ENV_RUNTIME_DATA_DIR) or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (_repo_root() / _DEFAULT_DATA_REL).resolve()


def get_state_dir() -> Path:
    """
    Ephemeral/process state (sessions, proposals).

    Precedence:
      1. SSN_STATE_DIR
      2. <runtime_data_dir>/state when SSN_RUNTIME_DATA_DIR is set
      3. <repo>/.ssn_state
    """
    override = (os.getenv(ENV_STATE_DIR) or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if (os.getenv(ENV_RUNTIME_DATA_DIR) or "").strip():
        return (get_runtime_data_dir() / "state").resolve()
    return (_repo_root() / _DEFAULT_STATE_REL).resolve()


def get_eval_output_dir() -> Path:
    override = (os.getenv(ENV_EVAL_OUTPUT_DIR) or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if (os.getenv(ENV_RUNTIME_DATA_DIR) or "").strip():
        return (get_runtime_data_dir() / "eval_reports").resolve()
    return (_repo_root() / _DEFAULT_EVAL_REL).resolve()


def runtime_data_path(*parts: str) -> str:
    """Join parts under the runtime data directory; ensure parent exists."""
    path = get_runtime_data_dir().joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def state_path(*parts: str) -> str:
    path = get_state_dir().joinpath(*parts)
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


def default_world_path() -> str:
    return runtime_data_path("world_model.json")


def default_identity_path() -> str:
    return runtime_data_path("identity_profile.json")


def default_trace_memory_path() -> str:
    return runtime_data_path("trace_memory.json")


def default_semantic_memory_path() -> str:
    return runtime_data_path("semantic_memory.json")


def default_audit_log_path() -> str:
    return runtime_data_path("audit.log")


def is_using_isolated_runtime_data() -> bool:
    return bool((os.getenv(ENV_RUNTIME_DATA_DIR) or "").strip())


@contextmanager
def isolated_runtime_data(
    *,
    prefix: str = "siona-runtime-",
    cleanup: bool = True,
) -> Iterator[Path]:
    """
    Create a temporary runtime-data directory and set env vars for the duration.

    Restores previous env on exit. Optionally removes the directory.
    """
    prev_data = os.environ.get(ENV_RUNTIME_DATA_DIR)
    prev_state = os.environ.get(ENV_STATE_DIR)
    prev_eval = os.environ.get(ENV_EVAL_OUTPUT_DIR)
    tmp = Path(tempfile.mkdtemp(prefix=prefix))
    data_dir = tmp / "data"
    state_dir = tmp / "state"
    eval_dir = tmp / "eval_reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)
    os.environ[ENV_RUNTIME_DATA_DIR] = str(data_dir)
    os.environ[ENV_STATE_DIR] = str(state_dir)
    os.environ[ENV_EVAL_OUTPUT_DIR] = str(eval_dir)
    try:
        yield data_dir
    finally:
        if prev_data is None:
            os.environ.pop(ENV_RUNTIME_DATA_DIR, None)
        else:
            os.environ[ENV_RUNTIME_DATA_DIR] = prev_data
        if prev_state is None:
            os.environ.pop(ENV_STATE_DIR, None)
        else:
            os.environ[ENV_STATE_DIR] = prev_state
        if prev_eval is None:
            os.environ.pop(ENV_EVAL_OUTPUT_DIR, None)
        else:
            os.environ[ENV_EVAL_OUTPUT_DIR] = prev_eval
        if cleanup:
            shutil.rmtree(tmp, ignore_errors=True)


def ensure_isolated_for_tests() -> Optional[Path]:
    """
    If SSN_RUNTIME_DATA_DIR is unset, allocate a temp dir and set env vars.
    Returns the data dir path (caller should clean up) or None if already set.
    """
    if is_using_isolated_runtime_data():
        return None
    tmp = Path(tempfile.mkdtemp(prefix="siona-ci-runtime-"))
    data_dir = tmp / "data"
    state_dir = tmp / "state"
    eval_dir = tmp / "eval_reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)
    os.environ[ENV_RUNTIME_DATA_DIR] = str(data_dir)
    os.environ[ENV_STATE_DIR] = str(state_dir)
    os.environ[ENV_EVAL_OUTPUT_DIR] = str(eval_dir)
    # Stash root for cleanup helpers
    os.environ["_SSN_RUNTIME_TMP_ROOT"] = str(tmp)
    return data_dir


def cleanup_ensured_isolation() -> None:
    root = os.environ.pop("_SSN_RUNTIME_TMP_ROOT", None)
    if root:
        shutil.rmtree(root, ignore_errors=True)
    # Only clear if we own them via tmp root cleanup path
    # Callers that used ensure_isolated_for_tests should clear env too:
    os.environ.pop(ENV_RUNTIME_DATA_DIR, None)
    os.environ.pop(ENV_STATE_DIR, None)
    os.environ.pop(ENV_EVAL_OUTPUT_DIR, None)
