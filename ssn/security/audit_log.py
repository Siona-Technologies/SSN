import time
import json
import os

LOG_PATH = "ssn/data/audit.log"


def _resolve_audit_path() -> str:
    try:
        from ssn.runtime.paths import default_audit_log_path

        return default_audit_log_path()
    except Exception:
        return LOG_PATH


class AuditLog:
    def __init__(self, path: str | None = None):
        self.path = path or _resolve_audit_path()
        parent = os.path.dirname(self.path) or "."
        os.makedirs(parent, exist_ok=True)

    def record(self, user_role, action, status, details=""):
        entry = {
            "timestamp": time.time(),
            "user_role": user_role,
            "action": action,
            "status": status,
            "details": details,
        }

        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

        return entry
