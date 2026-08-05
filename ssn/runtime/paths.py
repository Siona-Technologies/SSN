"""
Centralized runtime-data path resolution.

Default (normal users): repository-relative ``ssn/data`` and ``.ssn_state``.
Tests/smoke/CI: set ``SSN_RUNTIME_DATA_DIR`` to an isolated temporary directory.

Do not silently redirect permanent user data unless the env var is set.
Ownership-safe cleanup: only clear directories/env values this module allocated.
"""

from __future__ import annotations

import os
import shutil
import tempfile
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, Iterator, Optional


ENV_RUNTIME_DATA_DIR = "SSN_RUNTIME_DATA_DIR"
ENV_STATE_DIR = "SSN_STATE_DIR"
ENV_EVAL_OUTPUT_DIR = "SSN_EVAL_OUTPUT_DIR"
_OWNED_ROOT_ENV = "_SSN_RUNTIME_TMP_ROOT"
_OWNED_FLAG_ENV = "_SSN_RUNTIME_OWNED"

_DEFAULT_DATA_REL = Path("ssn") / "data"
_DEFAULT_STATE_REL = Path(".ssn_state")
_DEFAULT_EVAL_REL = Path("artifacts") / "eval"

_lock = threading.RLock()


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def get_runtime_data_dir() -> Path:
    override = (os.getenv(ENV_RUNTIME_DATA_DIR) or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (_repo_root() / _DEFAULT_DATA_REL).resolve()


def get_state_dir() -> Path:
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


def _allocate_dirs(prefix: str) -> Dict[str, Path]:
    tmp = Path(tempfile.mkdtemp(prefix=prefix))
    data_dir = tmp / "data"
    state_dir = tmp / "state"
    eval_dir = tmp / "eval_reports"
    data_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    eval_dir.mkdir(parents=True, exist_ok=True)
    return {"root": tmp, "data": data_dir, "state": state_dir, "eval": eval_dir}


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
    with _lock:
        prev_data = os.environ.get(ENV_RUNTIME_DATA_DIR)
        prev_state = os.environ.get(ENV_STATE_DIR)
        prev_eval = os.environ.get(ENV_EVAL_OUTPUT_DIR)
        dirs = _allocate_dirs(prefix)
        os.environ[ENV_RUNTIME_DATA_DIR] = str(dirs["data"])
        os.environ[ENV_STATE_DIR] = str(dirs["state"])
        os.environ[ENV_EVAL_OUTPUT_DIR] = str(dirs["eval"])
    try:
        yield dirs["data"]
    finally:
        with _lock:
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
                shutil.rmtree(dirs["root"], ignore_errors=True)


def ensure_isolated_for_tests() -> Optional[Path]:
    """
    If SSN_RUNTIME_DATA_DIR is unset, allocate a temp dir and claim ownership.
    If already set externally, leave it unchanged and do not claim ownership.
    """
    with _lock:
        if is_using_isolated_runtime_data():
            return None
        dirs = _allocate_dirs("siona-ci-runtime-")
        os.environ[ENV_RUNTIME_DATA_DIR] = str(dirs["data"])
        os.environ[ENV_STATE_DIR] = str(dirs["state"])
        os.environ[ENV_EVAL_OUTPUT_DIR] = str(dirs["eval"])
        os.environ[_OWNED_ROOT_ENV] = str(dirs["root"])
        os.environ[_OWNED_FLAG_ENV] = "1"
        return dirs["data"]


def cleanup_ensured_isolation() -> None:
    """
    Remove only directories/environment values owned by ensure_isolated_for_tests.
    Externally supplied SSN_* paths are left unchanged.
    """
    with _lock:
        owned = (os.environ.get(_OWNED_FLAG_ENV) or "").strip() == "1"
        root = os.environ.pop(_OWNED_ROOT_ENV, None)
        os.environ.pop(_OWNED_FLAG_ENV, None)
        if not owned:
            return
        if root:
            shutil.rmtree(root, ignore_errors=True)
        os.environ.pop(ENV_RUNTIME_DATA_DIR, None)
        os.environ.pop(ENV_STATE_DIR, None)
        os.environ.pop(ENV_EVAL_OUTPUT_DIR, None)


class PerTestIsolation:
    """
    Allocate unique runtime/state/eval dirs for a single test and restore after.
    """

    def __init__(self, *, prefix: str = "siona-test-") -> None:
        self.prefix = prefix
        self._dirs: Optional[Dict[str, Path]] = None
        self._prev: Dict[str, Optional[str]] = {}

    @property
    def data_dir(self) -> Optional[Path]:
        return None if self._dirs is None else self._dirs["data"]

    def start(self) -> Path:
        with _lock:
            self._prev = {
                ENV_RUNTIME_DATA_DIR: os.environ.get(ENV_RUNTIME_DATA_DIR),
                ENV_STATE_DIR: os.environ.get(ENV_STATE_DIR),
                ENV_EVAL_OUTPUT_DIR: os.environ.get(ENV_EVAL_OUTPUT_DIR),
            }
            self._dirs = _allocate_dirs(self.prefix)
            os.environ[ENV_RUNTIME_DATA_DIR] = str(self._dirs["data"])
            os.environ[ENV_STATE_DIR] = str(self._dirs["state"])
            os.environ[ENV_EVAL_OUTPUT_DIR] = str(self._dirs["eval"])
            return self._dirs["data"]

    def stop(self, *, cleanup: bool = True) -> None:
        with _lock:
            for key, prev in self._prev.items():
                if prev is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = prev
            root = self._dirs["root"] if self._dirs else None
            self._dirs = None
            self._prev = {}
        if cleanup and root is not None:
            shutil.rmtree(root, ignore_errors=True)
