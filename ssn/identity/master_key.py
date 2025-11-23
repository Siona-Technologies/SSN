"""
SSN Identity: Samson Master Key handling

This module NEVER stores the raw master key.
It only stores / compares a salted hash.

Dev notes:
- For now, the hash file is local and should NEVER be committed to Git.
- Later, this logic will be mirrored / hardened in Rust + a secure vault.
"""

from __future__ import annotations
import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import Optional, Tuple

# Where the hashed master key will be stored (LOCAL ONLY)
# This path must be added to .gitignore later.
DEFAULT_SECRET_DIR = Path("data/secret")
DEFAULT_MASTER_KEY_FILE = DEFAULT_SECRET_DIR / "master_key.json"

# PBKDF2 parameters (can be tuned later)
ALGO = "sha256"
ITERATIONS = 200_000
SALT_BYTES = 16
KEY_LEN = 32


class MasterKeyNotSet(Exception):
    """Raised when verification is attempted but no master key exists."""


def _derive_key(password: str, salt: bytes) -> bytes:
    """
    Derive a key from the given password and salt using PBKDF2-HMAC.
    """
    return hashlib.pbkdf2_hmac(
        ALGO,
        password.encode("utf-8"),
        salt,
        ITERATIONS,
        dklen=KEY_LEN,
    )


def _load_record(path: Path = DEFAULT_MASTER_KEY_FILE) -> Tuple[bytes, bytes]:
    """
    Load salt and hash from the master key file.

    Returns:
        (salt_bytes, hash_bytes)
    """
    if not path.exists():
        raise MasterKeyNotSet("Master key file does not exist yet.")

    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    salt = bytes.fromhex(data["salt"])
    key_hash = bytes.fromhex(data["hash"])

    return salt, key_hash


def _save_record(salt: bytes, key_hash: bytes, path: Path = DEFAULT_MASTER_KEY_FILE) -> None:
    """
    Save salt and hash to disk in JSON form.
    """
    DEFAULT_SECRET_DIR.mkdir(parents=True, exist_ok=True)

    record = {
        "salt": salt.hex(),
        "hash": key_hash.hex(),
        "algo": ALGO,
        "iterations": ITERATIONS,
        "key_len": KEY_LEN,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(record, f)


def is_master_key_initialized(path: Path = DEFAULT_MASTER_KEY_FILE) -> bool:
    """
    Check if the master key file already exists.
    """
    return path.exists()


def initialize_master_key(plain_key: str, path: Path = DEFAULT_MASTER_KEY_FILE) -> None:
    """
    One-time setup: create the Samson Master Key record.

    - Generates a random salt
    - Derives a hash using PBKDF2
    - Stores ONLY (salt, hash, params) in a local JSON file

    If the file already exists, this will NOT overwrite it unless
    the environment variable SSN_ALLOW_MASTER_KEY_RESET is set to '1'.
    """
    if path.exists() and os.getenv("SSN_ALLOW_MASTER_KEY_RESET") != "1":
        raise RuntimeError(
            "Master key already initialized. "
            "Set SSN_ALLOW_MASTER_KEY_RESET=1 if you really want to reset it."
        )

    salt = secrets.token_bytes(SALT_BYTES)
    key_hash = _derive_key(plain_key, salt)
    _save_record(salt, key_hash, path)


def verify_master_key(candidate_key: Optional[str]) -> bool:
    """
    Verify a candidate master key string.

    Returns:
        True  -> candidate matches Samson Master Key
        False -> candidate is wrong OR no key provided
    """
    if not candidate_key:
        return False

    try:
        salt, stored_hash = _load_record()
    except MasterKeyNotSet:
        # No master key configured yet
        return False

    candidate_hash = _derive_key(candidate_key, salt)
    # Use secrets.compare_digest to avoid timing attacks
    return secrets.compare_digest(candidate_hash, stored_hash)
