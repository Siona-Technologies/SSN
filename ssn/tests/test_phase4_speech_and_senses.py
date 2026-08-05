# ssn/tests/test_phase4_speech_and_senses.py

import os
import unittest
from unittest.mock import patch

from ssn.interfaces.contracts import InterfaceRequest
from ssn.interfaces.handlers_tools import handle_run_tool
from ssn.runtime.runtime_builder import SSNRuntimeBuilder
from ssn.runtime.voice_once import run_voice_once
from ssn.speech.backends import stt_listen, tts_speak
from ssn.tools.registry import ToolRegistry
from ssn.tools.speech_tools import register_speech_tools


class TestPhase4SpeechBackends(unittest.TestCase):
    def setUp(self):
        self._env = dict(os.environ)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self._env)

    def test_stt_dummy_backend_structured(self):
        os.environ["SSN_STT_BACKEND"] = "dummy"
        out = stt_listen(language="en")
        self.assertTrue(out["ok"])
        self.assertEqual(out["backend"], "dummy")
        self.assertIn("note", out)

    def test_stt_text_bypass(self):
        os.environ["SSN_STT_BACKEND"] = "dummy"
        out = stt_listen(language="en", text_override="hello world")
        self.assertTrue(out["ok"])
        self.assertEqual(out["transcript"], "hello world")
        self.assertEqual(out["backend"], "text")

    def test_tts_stdout_backend(self):
        os.environ["SSN_TTS_BACKEND"] = "stdout"
        out = tts_speak(text="Phase four test", language="en")
        self.assertTrue(out["ok"])
        self.assertTrue(out["spoken"])
        self.assertEqual(out["backend"], "stdout")


class TestPhase4SpeechTools(unittest.TestCase):
    def setUp(self):
        self.reg = ToolRegistry()
        register_speech_tools(self.reg)

    @patch("ssn.interfaces.handlers_tools.is_samson_verified", return_value=True)
    @patch("ssn.interfaces.handlers_tools.verify_owner", return_value={"overall_score": 1.0})
    def test_stt_tool_via_gateway(self, *_mocks):
        os.environ["SSN_STT_BACKEND"] = "dummy"
        deps = {"tool_registry": self.reg}
        req = InterfaceRequest(
            action="run_tool",
            role="OWNER",
            user_input="",
            context={
                "tool_name": "speech.stt.listen",
                "args": {"text": "synthetic transcript"},
            },
            meta={"master_key": "TEST"},
        )
        resp = handle_run_tool(req, deps)
        self.assertTrue(resp.ok)
        result = resp.data.get("result") or {}
        self.assertEqual(result.get("transcript"), "synthetic transcript")

    @patch("ssn.interfaces.handlers_tools.is_samson_verified", return_value=True)
    @patch("ssn.interfaces.handlers_tools.verify_owner", return_value={"overall_score": 1.0})
    def test_tts_tool_requires_approval_then_speaks(self, *_mocks):
        os.environ["SSN_TTS_BACKEND"] = "stdout"
        deps = {"tool_registry": self.reg}

        pending = InterfaceRequest(
            action="run_tool",
            role="OWNER",
            user_input="",
            context={"tool_name": "speech.tts.speak", "args": {"text": "hello"}},
            meta={"master_key": "TEST"},
        )
        blocked = handle_run_tool(pending, deps)
        self.assertFalse(blocked.ok)
        self.assertEqual(blocked.data.get("final_result"), "NEEDS_OWNER_APPROVAL")

        approved = InterfaceRequest(
            action="run_tool",
            role="OWNER",
            user_input="",
            context={
                "tool_name": "speech.tts.speak",
                "args": {"text": "hello"},
                "confirm": True,
            },
            meta={"master_key": "TEST"},
        )
        ok = handle_run_tool(approved, deps)
        self.assertTrue(ok.ok)
        result = ok.data.get("result") or {}
        self.assertTrue(result.get("spoken"))


class TestPhase4VoiceOnce(unittest.TestCase):
    @patch("ssn.interfaces.handlers_tools.is_samson_verified", return_value=True)
    @patch("ssn.interfaces.handlers_tools.verify_owner", return_value={"overall_score": 1.0})
    def test_voice_once_text_bypass_offline(self, *_mocks):
        os.environ.setdefault("SSN_OFFLINE", "1")
        os.environ["SSN_TTS_BACKEND"] = "stdout"
        rt = SSNRuntimeBuilder.build_default(default_role="GUEST", output_mode="full")
        deps = getattr(rt.gateway, "deps", None) or {}
        orch = deps.get("orchestrator")
        if orch is not None and getattr(orch, "tools", None) is not None:
            rt.gateway.deps["tool_registry"] = orch.tools

        out = run_voice_once(
            runtime=rt,
            master_key="TEST",
            text="hello",
            offline=True,
            speak=True,
        )
        self.assertTrue(out.get("ok"), out)
        self.assertEqual(out.get("transcript"), "hello")
        self.assertTrue(isinstance(out.get("answer"), str))


class TestPhase4SenseTickDemo(unittest.TestCase):
    def test_synthetic_events_update_world(self):
        os.environ.setdefault("SSN_OFFLINE", "1")
        rt = SSNRuntimeBuilder.build_default(default_role="OWNER", output_mode="full")
        import time

        ts = time.time()
        events = [
            {
                "type": "motion_event",
                "sensor_type": "vision",
                "ts": ts,
                "confidence": 0.7,
                "entity": {"id": "person:test", "entity": "person", "status": "present"},
            }
        ]
        # Patch owner verification so this exercise is independent of tracked
        # identity_profile.json (required under SSN_RUNTIME_DATA_DIR isolation).
        with patch(
            "ssn.interfaces.handlers_sense_tick.verify_owner",
            return_value={
                "master_key_score": 1.0,
                "biometric_score": 0.0,
                "behavior_score": 0.0,
                "overall_score": 0.7,
            },
        ), patch(
            "ssn.interfaces.handlers_sense_tick.is_samson_verified",
            return_value=True,
        ):
            resp = rt.shell.handle_event(
                {
                    "type": "sense_tick",
                    "role": "OWNER",
                    "context": {"events": events, "max_events": 10},
                    "meta": {},
                }
            )
        self.assertTrue(resp.ok)
        wm = getattr(rt, "world_model", None)
        if wm is not None and callable(getattr(wm, "snapshot", None)):
            snap = wm.snapshot(include_events=True, max_events=20)
            self.assertGreaterEqual(len(snap.get("events", [])), 1)


if __name__ == "__main__":
    unittest.main()
