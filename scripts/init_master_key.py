from __future__ import annotations

import os
from ssn.identity.master_key import initialize_master_key, is_master_key_initialized

def main() -> None:
    mk = (os.getenv("SSN_MASTER_KEY") or "").strip()
    if not mk:
        raise SystemExit("SSN_MASTER_KEY is empty. Set it in env first.")

    if is_master_key_initialized():
        print("Master key already initialized (data/secret/master_key.json exists).")
        return

    initialize_master_key(mk)
    print("OK: master key initialized (stored as salted hash).")

if __name__ == "__main__":
    main()
