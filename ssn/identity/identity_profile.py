# ssn/identity/identity_profile.py

from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
import time
from typing import Any, Dict, List


DEFAULT_IDENTITY_PATH = "ssn/data/identity_profile.json"


def _resolve_default_identity_path() -> str:
    try:
        from ssn.runtime.paths import default_identity_path

        return default_identity_path()
    except Exception:
        return DEFAULT_IDENTITY_PATH


def _now() -> float:
    return time.time()


def _canonical_json(obj: Any) -> bytes:
    """
    Stable canonicalization for signing/verifying.
    """
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def sign_profile(payload: Dict[str, Any], master_key: str) -> str:
    """
    HMAC-SHA256 over canonical JSON.
    """
    key = (master_key or "").encode("utf-8")
    msg = _canonical_json(payload)
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_profile(profile: Dict[str, Any], master_key: str) -> bool:
    """
    Verify profile["signature"] matches payload (profile without signature).
    """
    if not isinstance(profile, dict):
        return False
    sig = profile.get("signature")
    if not isinstance(sig, str) or not sig:
        return False

    payload = dict(profile)
    payload.pop("signature", None)

    expected = sign_profile(payload, master_key)
    return hmac.compare_digest(sig, expected)


def _atomic_write_json(path: str, data: Any) -> None:
    dir_name = os.path.dirname(path) or "."
    base_name = os.path.basename(path)
    os.makedirs(dir_name, exist_ok=True)

    fd = None
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix=base_name + ".", suffix=".tmp", dir=dir_name)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False, default=str, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())

        os.replace(tmp_path, path)

        # best-effort directory fsync
        try:
            dir_fd = os.open(dir_name, os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except Exception:
            pass

    finally:
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass


class IdentityProfileStore:
    """
    Phase 6.5B — Persisted, signed identity profile (creator/owner binding).

    Stored at: ssn/data/identity_profile.json

    This does NOT replace owner verification. It provides a stable, tamper-evident
    identity record that SSN can reference consistently.
    """

    def __init__(self, path: str | None = None):
        self.path = path or _resolve_default_identity_path()
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)

    def load(self) -> Dict[str, Any]:
        if not os.path.exists(self.path):
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def save(self, profile: Dict[str, Any]) -> None:
        if not isinstance(profile, dict):
            raise ValueError("profile must be a dict")
        _atomic_write_json(self.path, profile)

    def view(self) -> Dict[str, Any]:
        prof = self.load()
        if not prof:
            return {"available": False, "reason": "no_identity_profile", "path": self.path}
        return {"available": True, "path": self.path, "profile": prof}

    def enroll(
        self,
        *,
        master_key: str,
        owner_name: str,
        creator_name: str,
        system_name: str,
        mission: str,
        laws: List[str],
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Create/overwrite the identity profile.
        If a profile exists and force=False => return ALREADY_ENROLLED.
        """
        existing = self.load()
        if existing and not force:
            return {
                "ok": False,
                "code": "ALREADY_ENROLLED",
                "message": "Identity profile already exists. Use force=true to overwrite.",
                "path": self.path,
            }

        created_ts = float(existing.get("created_ts", _now()) if isinstance(existing, dict) else _now())
        updated_ts = _now()

        payload: Dict[str, Any] = {
            "owner_name": str(owner_name),
            "creator_name": str(creator_name),
            "system_name": str(system_name),
            "mission": str(mission),
            "laws": [str(x) for x in (laws or [])],
            "created_ts": created_ts,
            "updated_ts": updated_ts,
            "version": "6.5B",
        }

        # Sign payload (without signature field)
        payload["signature"] = sign_profile({k: v for k, v in payload.items() if k != "signature"}, master_key)

        self.save(payload)
        return {"ok": True, "status": "enrolled", "path": self.path, "profile": payload}
