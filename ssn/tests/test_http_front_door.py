# ssn/tests/test_http_front_door.py

import json
import os
import shutil
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib import error as urllib_error
from urllib import request as urllib_request

from ssn.runtime.http_server import SionaHTTPServerState, make_handler
from ssn.runtime.session_store import SessionStore


def _post_json(url: str, payload: dict, headers: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=15.0) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, body
    except urllib_error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(raw)
        except json.JSONDecodeError:
            body = {"ok": False, "error": {"message": raw}}
        return e.code, body


def _get_json(url: str) -> tuple[int, dict]:
    with urllib_request.urlopen(url, timeout=15.0) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))


class TestHTTPFrontDoor(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._tmpdir = tempfile.mkdtemp(prefix="siona_http_test_")
        cls._prev_state = os.environ.get("SSN_STATE_DIR")
        cls._prev_offline = os.environ.get("SSN_OFFLINE")
        cls._prev_mk = os.environ.get("SSN_MASTER_KEY")

        os.environ["SSN_STATE_DIR"] = cls._tmpdir
        os.environ["SSN_OFFLINE"] = "1"
        os.environ.pop("SSN_MASTER_KEY", None)

        cls.state = SionaHTTPServerState()
        handler = make_handler(cls.state)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        cls.port = cls.server.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        cls._thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.server.shutdown()
        cls.server.server_close()
        if cls._prev_state is None:
            os.environ.pop("SSN_STATE_DIR", None)
        else:
            os.environ["SSN_STATE_DIR"] = cls._prev_state
        if cls._prev_offline is None:
            os.environ.pop("SSN_OFFLINE", None)
        else:
            os.environ["SSN_OFFLINE"] = cls._prev_offline
        if cls._prev_mk is None:
            os.environ.pop("SSN_MASTER_KEY", None)
        else:
            os.environ["SSN_MASTER_KEY"] = cls._prev_mk
        shutil.rmtree(cls._tmpdir, ignore_errors=True)

    def test_health(self) -> None:
        status, body = _get_json(f"{self.base}/v1/health")
        self.assertEqual(status, 200)
        self.assertTrue(body.get("ok"))
        self.assertEqual(body.get("service"), "siona-http-front-door")

    def test_chat_guest_returns_answer(self) -> None:
        status, body = _post_json(
            f"{self.base}/v1/chat",
            {"message": "hello from http test", "role": "GUEST", "offline": True},
        )
        self.assertEqual(status, 200)
        self.assertTrue(body.get("ok"))
        self.assertIsInstance(body.get("answer"), str)
        self.assertTrue(str(body.get("answer")).strip())
        self.assertEqual(body.get("turn_id"), 1)
        self.assertIn("session_id", body)

    def test_chat_session_turn_increments(self) -> None:
        sid = "test-session-001"
        _, body1 = _post_json(
            f"{self.base}/v1/chat",
            {"message": "first", "role": "GUEST", "session_id": sid, "offline": True},
        )
        _, body2 = _post_json(
            f"{self.base}/v1/chat",
            {"message": "second", "role": "GUEST", "session_id": sid, "offline": True},
        )
        self.assertEqual(body1.get("session_id"), sid)
        self.assertEqual(body2.get("session_id"), sid)
        self.assertEqual(body1.get("turn_id"), 1)
        self.assertEqual(body2.get("turn_id"), 2)

    def test_chat_missing_message_400(self) -> None:
        status, body = _post_json(f"{self.base}/v1/chat", {"role": "GUEST"})
        self.assertEqual(status, 400)
        self.assertFalse(body.get("ok"))

    def test_chat_with_mock_llm(self) -> None:
        from ssn.runtime.mock_llm_server import MockLLMHandler

        llm_server = ThreadingHTTPServer(("127.0.0.1", 0), MockLLMHandler)
        llm_port = llm_server.server_address[1]
        llm_thread = threading.Thread(target=llm_server.serve_forever, daemon=True)
        llm_thread.start()

        prev_provider = os.environ.get("SSN_LLM_PROVIDER")
        prev_endpoint = os.environ.get("SSN_LLM_ENDPOINT")
        os.environ["SSN_LLM_PROVIDER"] = "http"
        os.environ["SSN_LLM_ENDPOINT"] = f"http://127.0.0.1:{llm_port}/generate"
        self.state.runtime = None  # rebuild with http provider

        try:
            status, body = _post_json(
                f"{self.base}/v1/chat",
                {"message": "mock path", "role": "GUEST", "offline": True},
            )
            self.assertEqual(status, 200)
            self.assertIn("[MockLLM GUEST]", str(body.get("answer")))
        finally:
            llm_server.shutdown()
            llm_server.server_close()
            if prev_provider is None:
                os.environ.pop("SSN_LLM_PROVIDER", None)
            else:
                os.environ["SSN_LLM_PROVIDER"] = prev_provider
            if prev_endpoint is None:
                os.environ.pop("SSN_LLM_ENDPOINT", None)
            else:
                os.environ["SSN_LLM_ENDPOINT"] = prev_endpoint
            self.state.runtime = None

    def test_tool_run_guest_public_list(self) -> None:
        status, body = _post_json(
            f"{self.base}/v1/tool/run",
            {
                "tool_name": "tools.public_list",
                "role": "GUEST",
                "args": {},
                "offline": True,
                "allow_tools": True,
                "allow_research": True,
            },
        )
        # Policy may deny guest tools today; either success or structured denial is acceptable.
        self.assertIn(status, (200, 400))
        self.assertIn("session_id", body)
        self.assertIn("data", body)

    def test_tool_run_missing_name_400(self) -> None:
        status, body = _post_json(f"{self.base}/v1/tool/run", {"role": "GUEST"})
        self.assertEqual(status, 400)
        self.assertFalse(body.get("ok"))

    def test_tenant_session_isolation(self) -> None:
        _, body_a = _post_json(
            f"{self.base}/v1/chat",
            {"message": "tenant a", "role": "GUEST", "offline": True},
            headers={"X-SSN-Tenant-ID": "tenant-a"},
        )
        _, body_b = _post_json(
            f"{self.base}/v1/chat",
            {"message": "tenant b", "role": "GUEST", "offline": True},
            headers={"X-SSN-Tenant-ID": "tenant-b"},
        )
        self.assertEqual(body_a.get("tenant_id"), "tenant-a")
        self.assertEqual(body_b.get("tenant_id"), "tenant-b")
        self.assertNotEqual(body_a.get("session_id"), body_b.get("session_id"))

    def test_unknown_path_404(self) -> None:
        status, body = _post_json(f"{self.base}/v1/unknown", {"message": "x"})
        self.assertEqual(status, 404)


class TestSessionStore(unittest.TestCase):
    def test_bump_turn_persists(self) -> None:
        tmp = tempfile.mkdtemp(prefix="siona_sess_")
        try:
            os.environ["SSN_STATE_DIR"] = tmp
            store = SessionStore()
            sid = "abc-123"
            t1 = store.bump_turn(sid)
            t2 = store.bump_turn(sid)
            self.assertEqual(t1, 1)
            self.assertEqual(t2, 2)
            store2 = SessionStore()
            rec = store2.get_or_create(sid)
            self.assertEqual(rec.get("turn_id"), 2)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
