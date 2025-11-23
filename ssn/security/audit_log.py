import time
import json
import os

LOG_PATH = "ssn/data/audit.log"

class AuditLog:
    def __init__(self):
        os.makedirs("ssn/data", exist_ok=True)

    def record(self, user_role, action, status, details=""):
        entry = {
            "timestamp": time.time(),
            "user_role": user_role,
            "action": action,
            "status": status,
            "details": details
        }

        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(entry) + "\n")

        return entry
