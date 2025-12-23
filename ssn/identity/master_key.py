"""
SSN Identity: Samson Master Key handling

This module NEVER stores the raw master key.
It only stores / compares a salted hash.

It supports:
- Persistent hashed record stored under SSN_STATE_DIR (recommended)
- Env fallback (SSN_MASTER_KEY) when the record is not initialized yet
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import Optional, Tuple

# PBKDF2 parameters
ALGO = "sha256"
ITERATIONS = 200_000
SALT_BYTES = 16
KEY_LEN = 32


class MasterKeyNotSet(Exception):
    """Raised when verification is attempted but no master key exists."""


def _state_dir() -> Path:
    # Prefer SSN_STATE_DIR (your repo uses this already)
    v = (os.getenv("SSN_STATE_DIR") or "").strip()
    if v:
        return Path(v).expanduser()
    # Safe default (repo-local)
    return Path(".ssn_state")


def _secret_dir() -> Path:
    # Keep secrets inside state dir so .gitignore can cover it
    return _state_dir() / "secret"


def _default_master_key_file() -> Path:
    # Allow override if you ever want it
    override = (os.getenv("SSN_MASTER_KEY_FILE") or "").strip()
    if override:
        return Path(override).expanduser()
    return _secret_dir() / "master_key.json"


def _derive_key(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac(
        ALGO,
        password.encode("utf-8"),
        salt,
        ITERATIONS,
        dklen=KEY_LEN,
    )


def _load_record(path: Optional[Path] = None) -> Tuple[bytes, bytes]:
    p = path or _default_master_key_file()
    if not p.exists():
        raise MasterKeyNotSet("Master key file does not exist yet.")

    with p.open("r", encoding="utf-8") as f:
        data = json.load(f)

    salt = bytes.fromhex(data["salt"])
    key_hash = bytes.fromhex(data["hash"])
    return salt, key_hash


def _save_record(salt: bytes, key_hash: bytes, path: Optional[Path] = None) -> None:
    p = path or _default_master_key_file()
    p.parent.mkdir(parents=True, exist_ok=True)

    record = {
        "salt": salt.hex(),
        "hash": key_hash.hex(),
        "algo": ALGO,
        "iterations": ITERATIONS,
        "key_len": KEY_LEN,
    }
    with p.open("w", encoding="utf-8") as f:
        json.dump(record, f)


def is_master_key_initialized(path: Optional[Path] = None) -> bool:
    p = path or _default_master_key_file()
    return p.exists()


def initialize_master_key(plain_key: str, path: Optional[Path] = None) -> None:
    """
    One-time setup: create the Samson Master Key record (salt+hash only).

    If the file already exists, this will NOT overwrite it unless
    SSN_ALLOW_MASTER_KEY_RESET=1.
    """
    p = path or _default_master_key_file()
    if p.exists() and os.getenv("SSN_ALLOW_MASTER_KEY_RESET") != "1":
        raise RuntimeError(
            "Master key already initialized. "
            "Set SSN_ALLOW_MASTER_KEY_RESET=1 if you really want to reset it."
        )

    salt = secrets.token_bytes(SALT_BYTES)
    key_hash = _derive_key(plain_key, salt)
    _save_record(salt, key_hash, p)


def verify_master_key(candidate_key: Optional[str]) -> bool:
    """
    Verify a candidate master key string.

    Priority:
      1) If hashed record exists -> verify against record
      2) Else fallback to env SSN_MASTER_KEY (plaintext compare, not stored)
    """
    if not candidate_key:
        return False

    # 1) Try persistent record first
    try:
        salt, stored_hash = _load_record()
        candidate_hash = _derive_key(candidate_key, salt)
        return secrets.compare_digest(candidate_hash, stored_hash)
    except MasterKeyNotSet:
        pass
    except Exception:
        # Fail closed on unexpected corruption
        return False

    # 2) Env fallback (useful for first-time bootstrap)
    env_key = (os.getenv("SSN_MASTER_KEY") or "").strip()
    if env_key:
        return secrets.compare_digest(candidate_key, env_key)

    return False
