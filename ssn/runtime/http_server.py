"""
SIONA HTTP Front Door — platform API (Phase 2).

Endpoints:
  GET  /v1/health
  POST /v1/chat
  POST /v1/tool/run

Stdlib only. Same Front Door path as CLI.
"""

from __future__ import annotations

import argparse
import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Dict, Optional, Tuple, Type
from urllib.parse import urlparse

from ssn.interfaces.contracts import InterfaceRequest
from ssn.interfaces.front_door import handle_user_message
from ssn.runtime.frontdoor_context import (
    forced_offline,
    get_env_master_key,
    mk_frontdoor_context,
    mk_tool_request_context,
    normalize_role,
    normalize_session_id,
)
from ssn.runtime.runtime_builder import SSNRuntime, SSNRuntimeBuilder
from ssn.runtime.session_store import SessionStore
from ssn.runtime.structured_logging import emit_audit, emit_http_access, emit_log, structured_logging_enabled
from ssn.runtime.tenant_config import load_tenant_config, resolve_tenant_id

_MAX_BODY_BYTES = 256_000


class SionaHTTPServerState:
    """Shared app state for the HTTP server."""

    def __init__(self) -> None:
        self.runtime: Optional[SSNRuntime] = None
        self._session_stores: Dict[str, SessionStore] = {}
        self._lock = threading.Lock()

    def get_runtime(self) -> SSNRuntime:
        with self._lock:
            if self.runtime is None:
                self.runtime = SSNRuntimeBuilder.build_default(default_role="GUEST")
            return self.runtime

    def session_store_for(self, tenant_header: Optional[str] = None) -> SessionStore:
        tid = resolve_tenant_id(header_value=tenant_header)
        cfg = load_tenant_config(tenant_id=tid)
        key = cfg.tenant_id or "default"
        with self._lock:
            store = self._session_stores.get(key)
            if store is None:
                store = SessionStore(base_dir=os.path.join(cfg.state_dir, "sessions"))
                self._session_stores[key] = store
            return store


def _read_json_body(handler: BaseHTTPRequestHandler, *, max_bytes: int = _MAX_BODY_BYTES) -> Tuple[bool, Dict[str, Any], str]:
    try:
        length = int(handler.headers.get("Content-Length") or "0")
    except ValueError:
        length = 0
    if length <= 0:
        return False, {}, "empty body"
    if length > max_bytes:
        return False, {}, "body too large"
    raw = handler.rfile.read(length)
    try:
        obj = json.loads(raw.decode("utf-8"))
    except json.JSONDecodeError:
        return False, {}, "invalid json"
    if not isinstance(obj, dict):
        return False, {}, "body must be a json object"
    return True, obj, ""


def _extract_master_key(headers: Any, body: Dict[str, Any]) -> Optional[str]:
    for header_name in ("X-SSN-Master-Key", "X-Ssn-Master-Key"):
        v = headers.get(header_name)
        if isinstance(v, str) and v.strip():
            return v.strip()

    auth = headers.get("Authorization")
    if isinstance(auth, str) and auth.lower().startswith("bearer "):
        token = auth[7:].strip()
        if token:
            return token

    mk = body.get("master_key")
    if isinstance(mk, str) and mk.strip():
        return mk.strip()

    meta = body.get("meta")
    if isinstance(meta, dict):
        mkm = meta.get("master_key")
        if isinstance(mkm, str) and mkm.strip():
            return mkm.strip()

    role = normalize_role(body.get("role"))
    if role == "OWNER":
        return get_env_master_key()
    return None


def _bool_field(body: Dict[str, Any], key: str, default: bool) -> bool:
    v = body.get(key, default)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        s = v.strip().lower()
        if s in ("1", "true", "yes", "on"):
            return True
        if s in ("0", "false", "no", "off"):
            return False
    return bool(default)


def _chat_response(
    *,
    state: SionaHTTPServerState,
    body: Dict[str, Any],
    headers: Any,
) -> Tuple[int, Dict[str, Any]]:
    message = body.get("message")
    if not isinstance(message, str) or not message.strip():
        return 400, {"ok": False, "error": {"code": "BAD_REQUEST", "message": "message is required"}}

    tenant_header = headers.get("X-SSN-Tenant-ID") or headers.get("X-Ssn-Tenant-Id")
    session_store = state.session_store_for(tenant_header)
    tid = resolve_tenant_id(header_value=tenant_header)

    session_id = normalize_session_id(body.get("session_id"))
    turn_id = session_store.bump_turn(session_id)

    role = normalize_role(body.get("role"))
    master_key = _extract_master_key(headers, body)
    if role == "OWNER" and not master_key:
        role = "GUEST"

    offline = _bool_field(body, "offline", forced_offline()) or forced_offline()
    strict = _bool_field(body, "strict", False)
    allow_tools = _bool_field(body, "allow_tools", True)
    allow_research = _bool_field(body, "allow_research", True)

    extra = body.get("context")
    extra_context = extra if isinstance(extra, dict) else None

    ctx = mk_frontdoor_context(
        session_id=session_id,
        turn_id=turn_id,
        role=role,
        offline=offline,
        strict=strict,
        allow_tools=allow_tools,
        allow_research=allow_research,
        master_key=master_key,
        extra_context=extra_context,
    )

    rt = state.get_runtime()
    deps = getattr(rt.gateway, "deps", None) or {}
    if "orchestrator" not in deps:
        return 500, {"ok": False, "error": {"code": "RUNTIME_ERROR", "message": "orchestrator not wired"}}

    out = handle_user_message(message.strip(), deps, ctx)
    session_state = out.get("session_state") if isinstance(out.get("session_state"), dict) else {}
    session_store.save_session_state(session_id, session_state)

    return 200, {
        "ok": True,
        "tenant_id": tid,
        "session_id": session_id,
        "turn_id": turn_id,
        "answer": out.get("answer"),
        "degraded": bool(out.get("degraded", False)),
        "used_tools": out.get("used_tools") if isinstance(out.get("used_tools"), list) else [],
        "citations": out.get("citations") if isinstance(out.get("citations"), list) else [],
        "sources": out.get("sources") if isinstance(out.get("sources"), list) else [],
        "note": out.get("note"),
        "session_state": session_state,
    }


def _tool_response(
    *,
    state: SionaHTTPServerState,
    body: Dict[str, Any],
    headers: Any,
) -> Tuple[int, Dict[str, Any]]:
    tool_name = body.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.strip():
        return 400, {"ok": False, "error": {"code": "BAD_REQUEST", "message": "tool_name is required"}}

    tenant_header = headers.get("X-SSN-Tenant-ID") or headers.get("X-Ssn-Tenant-Id")
    session_store = state.session_store_for(tenant_header)
    tid = resolve_tenant_id(header_value=tenant_header)

    session_id = normalize_session_id(body.get("session_id"))
    turn_id = session_store.bump_turn(session_id)

    role = normalize_role(body.get("role"))
    master_key = _extract_master_key(headers, body)
    if role == "OWNER" and not master_key:
        role = "GUEST"

    args = body.get("args")
    if args is not None and not isinstance(args, dict):
        return 400, {"ok": False, "error": {"code": "BAD_REQUEST", "message": "args must be an object"}}

    offline = _bool_field(body, "offline", forced_offline()) or forced_offline()
    strict = _bool_field(body, "strict", False)
    allow_tools = _bool_field(body, "allow_tools", True)
    allow_research = _bool_field(body, "allow_research", True)
    confirm = _bool_field(body, "confirm", False)

    extra = body.get("context")
    extra_context = extra if isinstance(extra, dict) else None

    ctx = mk_tool_request_context(
        session_id=session_id,
        turn_id=turn_id,
        tool_name=tool_name.strip(),
        args=args if isinstance(args, dict) else {},
        role=role,
        offline=offline,
        strict=strict,
        allow_tools=allow_tools,
        allow_research=allow_research,
        master_key=master_key,
        confirm=confirm,
        extra_context=extra_context,
    )

    meta: Dict[str, Any] = {}
    if master_key:
        meta["master_key"] = master_key

    req = InterfaceRequest(
        action="run_tool",
        role=role,
        user_input="",
        context=ctx,
        session_id=session_id,
        turn_id=str(turn_id),
        offline=offline,
        strict=strict,
        allow_tools=allow_tools,
        allow_research=allow_research,
        confirm=confirm,
        meta=meta,
    )

    rt = state.get_runtime()
    resp = rt.gateway.handle(req)

    data = resp.data if isinstance(resp.data, dict) else {}
    err = None if resp.error is None else resp.error.to_dict()

    return (200 if resp.ok else 400), {
        "ok": bool(resp.ok),
        "tenant_id": tid,
        "session_id": session_id,
        "turn_id": turn_id,
        "action": resp.action,
        "role": resp.role,
        "data": data,
        "error": err,
    }


def make_handler(state: SionaHTTPServerState) -> Type[BaseHTTPRequestHandler]:
    class SionaHTTPHandler(BaseHTTPRequestHandler):
        server_version = "SIONA-HTTP/1.0"

        def log_message(self, fmt: str, *args: Any) -> None:
            if os.getenv("SSN_HTTP_QUIET") == "1":
                return
            if structured_logging_enabled():
                return
            super().log_message(fmt, *args)

        def _send_json(self, status: int, obj: Dict[str, Any]) -> None:
            body = json.dumps(obj, ensure_ascii=False, default=str).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _log_access(self, *, status: int, started: float, extra: Optional[Dict[str, Any]] = None) -> None:
            path = urlparse(self.path).path
            emit_http_access(
                method=self.command,
                path=path,
                status=status,
                duration_ms=(time.time() - started) * 1000.0,
                tenant_id=(extra or {}).get("tenant_id"),
                session_id=(extra or {}).get("session_id"),
                extra={k: v for k, v in (extra or {}).items() if k not in ("tenant_id", "session_id")},
            )

        def do_GET(self) -> None:
            started = time.time()
            path = urlparse(self.path).path
            if path in ("/v1/health", "/health", "/healthz"):
                try:
                    from ssn.integration.runtime_modes import get_runtime_mode

                    cog_mode = get_runtime_mode().value
                except Exception:
                    cog_mode = "legacy"
                self._send_json(
                    200,
                    {
                        "ok": True,
                        "service": "siona-http-front-door",
                        "offline": forced_offline(),
                        "cognitive_mode": cog_mode,
                    },
                )
                self._log_access(status=200, started=started)
                return
            self._send_json(404, {"ok": False, "error": {"code": "NOT_FOUND", "message": "unknown path"}})
            self._log_access(status=404, started=started)

        def do_POST(self) -> None:
            started = time.time()
            path = urlparse(self.path).path
            ok, body, err = _read_json_body(self)
            if not ok:
                self._send_json(400, {"ok": False, "error": {"code": "BAD_REQUEST", "message": err}})
                self._log_access(status=400, started=started, extra={"route": path})
                return

            if path == "/v1/chat":
                status, out = _chat_response(state=state, body=body, headers=self.headers)
                self._send_json(status, out)
                self._log_access(
                    status=status,
                    started=started,
                    extra={
                        "tenant_id": out.get("tenant_id"),
                        "session_id": out.get("session_id"),
                        "route": "/v1/chat",
                    },
                )
                emit_audit(
                    action="chat",
                    ok=bool(out.get("ok")) and status < 400,
                    role=str(body.get("role") or "GUEST"),
                    tenant_id=out.get("tenant_id") if isinstance(out.get("tenant_id"), str) else None,
                    session_id=out.get("session_id") if isinstance(out.get("session_id"), str) else None,
                    turn_id=out.get("turn_id") if isinstance(out.get("turn_id"), int) else None,
                    degraded=bool(out.get("degraded", False)),
                    extra={"status": status},
                )
                return

            if path == "/v1/tool/run":
                status, out = _tool_response(state=state, body=body, headers=self.headers)
                self._send_json(status, out)
                self._log_access(
                    status=status,
                    started=started,
                    extra={
                        "tenant_id": out.get("tenant_id"),
                        "session_id": out.get("session_id"),
                        "route": "/v1/tool/run",
                    },
                )
                data = out.get("data") if isinstance(out.get("data"), dict) else {}
                emit_audit(
                    action="run_tool",
                    ok=bool(out.get("ok")) and status < 400,
                    role=str(out.get("role") or body.get("role") or "GUEST"),
                    tenant_id=out.get("tenant_id") if isinstance(out.get("tenant_id"), str) else None,
                    session_id=out.get("session_id") if isinstance(out.get("session_id"), str) else None,
                    turn_id=out.get("turn_id") if isinstance(out.get("turn_id"), int) else None,
                    tool_name=str(body.get("tool_name") or ""),
                    extra={"status": status, "allowed": data.get("allowed")},
                )
                return

            self._send_json(404, {"ok": False, "error": {"code": "NOT_FOUND", "message": "unknown path"}})
            self._log_access(status=404, started=started, extra={"route": path})

    return SionaHTTPHandler


def serve(host: str = "127.0.0.1", port: int = 8080) -> None:
    state = SionaHTTPServerState()
    handler = make_handler(state)
    server = ThreadingHTTPServer((host, port), handler)
    emit_log("service.start", host=host, port=port, offline=forced_offline())
    print(f"SIONA HTTP Front Door listening on http://{host}:{port}")
    print("  GET  /v1/health")
    print("  POST /v1/chat")
    print("  POST /v1/tool/run")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
    finally:
        server.server_close()


def main() -> None:
    parser = argparse.ArgumentParser(description="SIONA HTTP Front Door")
    parser.add_argument("--host", default=os.getenv("SSN_HTTP_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.getenv("SSN_HTTP_PORT", "8080")))
    args = parser.parse_args()
    serve(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
