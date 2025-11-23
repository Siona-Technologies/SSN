"""
SSN Backup Manager (Phase 1)

Creates encrypted backups of core memory and vault files.

Backed up:
- ssn/data/semantic_memory.json
- ssn/data/episodic_memory.json
- ssn/data/personal_profile.json
- data/secret/secret_vault.json   (from vault module)

Encrypted with a dedicated backup key using Fernet.
"""

from __future__ import annotations
import os
import json
import time
from typing import List, Dict, Any

from cryptography.fernet import Fernet


SEMANTIC_PATH = "ssn/data/semantic_memory.json"
EPISODIC_PATH = "ssn/data/episodic_memory.json"
PROFILE_PATH = "ssn/data/personal_profile.json"
VAULT_PATH = "data/secret/secret_vault.json"  # from vault module

BACKUP_DIR = "ssn/data/backups"
BACKUP_KEY_PATH = "ssn/data/backup.key"


class BackupManager:
    def __init__(self):
        os.makedirs(os.path.dirname(BACKUP_KEY_PATH), exist_ok=True)
        os.makedirs(BACKUP_DIR, exist_ok=True)

        # Load or create backup key
        if not os.path.exists(BACKUP_KEY_PATH):
            key = Fernet.generate_key()
            with open(BACKUP_KEY_PATH, "wb") as f:
                f.write(key)
        else:
            with open(BACKUP_KEY_PATH, "rb") as f:
                key = f.read()

        self.fernet = Fernet(key)

    # --------------------- internal helpers ---------------------

    def _read_file_if_exists(self, path: str):
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return None

    # --------------------- public api ---------------------------

    def create_backup(self, label: str = "manual") -> str:
        """
        Create an encrypted backup snapshot.
        Returns the backup filename.
        """
        snapshot = {
            "timestamp": time.time(),
            "label": label,
            "semantic": self._read_file_if_exists(SEMANTIC_PATH),
            "episodic": self._read_file_if_exists(EPISODIC_PATH),
            "profile": self._read_file_if_exists(PROFILE_PATH),
            "vault": self._read_file_if_exists(VAULT_PATH),
        }

        raw = json.dumps(snapshot).encode("utf-8")
        encrypted = self.fernet.encrypt(raw)

        filename = f"{int(snapshot['timestamp'])}_{label}.bak"
        backup_path = os.path.join(BACKUP_DIR, filename)

        with open(backup_path, "wb") as f:
            f.write(encrypted)

        return backup_path

    def list_backups(self) -> List[str]:
        """Return list of backup filenames."""
        if not os.path.exists(BACKUP_DIR):
            return []
        return sorted(os.listdir(BACKUP_DIR))

    def load_backup(self, filename: str) -> Dict[str, Any]:
        """
        Decrypt and return snapshot content without restoring it.
        (Safe read-only view.)
        """
        path = os.path.join(BACKUP_DIR, filename)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Backup file not found: {path}")

        with open(path, "rb") as f:
            encrypted = f.read()

        raw = self.fernet.decrypt(encrypted)
        return json.loads(raw.decode("utf-8"))
