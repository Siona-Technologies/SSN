# ssn/tests/test_phase6_production_shape.py

import io
import json
import os
import unittest
from contextlib import redirect_stdout

from ssn.runtime.structured_logging import emit_audit, emit_log, scrub_value, structured_logging_enabled


class TestPhase6StructuredLogging(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def test_disabled_by_default(self):
        os.environ.pop("SSN_STRUCTURED_LOG", None)
        os.environ.pop("SSN_HTTP_STRUCTURED_LOG", None)
        self.assertFalse(structured_logging_enabled())

    def test_enabled_with_env_flag(self):
        os.environ["SSN_STRUCTURED_LOG"] = "1"
        self.assertTrue(structured_logging_enabled())

    def test_scrub_master_key(self):
        out = scrub_value({"master_key": "secret-value", "session_id": "abc"})
        self.assertEqual(out["master_key"], "<redacted>")
        self.assertEqual(out["session_id"], "abc")

    def test_emit_log_json_line(self):
        os.environ["SSN_STRUCTURED_LOG"] = "1"
        buf = io.StringIO()
        with redirect_stdout(buf):
            emit_log("test.event", role="OWNER", master_key="hidden")
        line = buf.getvalue().strip()
        obj = json.loads(line)
        self.assertEqual(obj["event"], "test.event")
        self.assertEqual(obj["role"], "OWNER")
        self.assertEqual(obj["master_key"], "<redacted>")

    def test_emit_audit_event(self):
        os.environ["SSN_STRUCTURED_LOG"] = "1"
        buf = io.StringIO()
        with redirect_stdout(buf):
            emit_audit(
                action="chat",
                ok=True,
                role="GUEST",
                session_id="s1",
                turn_id=2,
            )
        obj = json.loads(buf.getvalue().strip())
        self.assertEqual(obj["event"], "audit")
        self.assertEqual(obj["action"], "chat")
        self.assertTrue(obj["ok"])


class TestPhase6DeployArtifacts(unittest.TestCase):
    def test_systemd_unit_exists(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        path = os.path.join(root, "deploy", "siona.service")
        self.assertTrue(os.path.isfile(path))
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("ssn.runtime.http_server", text)

    def test_backup_script_exists(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        path = os.path.join(root, "scripts", "backup_state.sh")
        self.assertTrue(os.path.isfile(path))

    def test_pyproject_entry_points(self):
        root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        path = os.path.join(root, "pyproject.toml")
        self.assertTrue(os.path.isfile(path))
        with open(path, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("siona-cli", text)
        self.assertIn("siona-http", text)


if __name__ == "__main__":
    unittest.main()
