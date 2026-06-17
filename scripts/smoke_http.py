#!/usr/bin/env python3
"""
Smoke test for SIONA HTTP Front Door.

Starts server in-process, hits health + chat, prints JSON summary.
"""

from __future__ import annotations

import json
import os
import sys
import threading
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib import request as urllib_request

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ssn.runtime.http_server import SionaHTTPServerState, make_handler


def main() -> int:
    os.environ.setdefault("SSN_OFFLINE", "1")
    os.environ.pop("SSN_MASTER_KEY", None)

    state = SionaHTTPServerState()
    handler = make_handler(state)
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    port = server.server_address[1]
    base = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        with urllib_request.urlopen(f"{base}/v1/health", timeout=10) as resp:
            health = json.loads(resp.read().decode("utf-8"))
        print("health:", json.dumps(health, indent=2))

        payload = json.dumps(
            {"message": "smoke test hello", "role": "GUEST", "offline": True}
        ).encode("utf-8")
        req = urllib_request.Request(
            f"{base}/v1/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib_request.urlopen(req, timeout=30) as resp:
            chat = json.loads(resp.read().decode("utf-8"))

        print("chat:", json.dumps({k: chat.get(k) for k in ("ok", "session_id", "turn_id", "answer")}, indent=2))

        if not chat.get("ok") or not str(chat.get("answer", "")).strip():
            print("FAIL: chat did not return ok answer", file=sys.stderr)
            return 1
        print("OK: HTTP Front Door smoke passed")
        return 0
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())
