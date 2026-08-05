"""Phase 3A — runtime-data isolation regression tests."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("SSN_OFFLINE", "1")

ROOT = Path(__file__).resolve().parents[2]
PY = Path(r"C:\Users\njaji\Documents\SSN\.venv\Scripts\python.exe")
if not PY.exists():
    PY = Path(sys.executable)


class TestRuntimeDataPaths(unittest.TestCase):
    def test_default_path_backward_compatible(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("SSN_RUNTIME_DATA_DIR", None)
            from importlib import reload
            import ssn.runtime.paths as paths

            reload(paths)
            data = paths.get_runtime_data_dir()
            self.assertTrue(str(data).replace("\\", "/").endswith("ssn/data"))
            self.assertFalse(paths.is_using_isolated_runtime_data())

    def test_two_temp_dirs_do_not_share_state(self):
        from ssn.runtime.paths import isolated_runtime_data
        from ssn.world.world_model import WorldModel

        with isolated_runtime_data(prefix="iso-a-") as a:
            wa = WorldModel()
            wa.apply_update(
                {
                    "type": "world_update",
                    "ts": 1.0,
                    "source": "test",
                    "entities": [
                        {
                            "id": "e-a",
                            "entity": "marker",
                            "status": "present",
                            "confidence": 0.9,
                            "attributes": {},
                        }
                    ],
                    "events": [],
                }
            )
            path_a = wa.path
            self.assertTrue(Path(path_a).exists())
            snap_a = wa.snapshot(max_entities=10, max_events=10)

        with isolated_runtime_data(prefix="iso-b-") as b:
            wb = WorldModel()
            path_b = wb.path
            self.assertNotEqual(path_a, path_b)
            snap_b = wb.snapshot(max_entities=10, max_events=10)
            # New isolated dir should not see entity from dir A
            ids = [e.get("id") for e in (snap_b.get("entities") or [])]
            self.assertNotIn("e-a", ids)

    def test_failed_test_still_cleans_temp(self):
        from ssn.runtime.paths import ENV_RUNTIME_DATA_DIR, isolated_runtime_data

        prev = os.environ.get(ENV_RUNTIME_DATA_DIR)
        created = {"path": None}
        try:
            with isolated_runtime_data(prefix="iso-fail-", cleanup=True) as d:
                created["path"] = str(d)
                raise RuntimeError("boom")
        except RuntimeError:
            pass
        self.assertIsNotNone(created["path"])
        self.assertFalse(Path(created["path"]).exists())
        # Nested isolation restores prior env (may be CI isolation, not unset)
        self.assertEqual(os.environ.get(ENV_RUNTIME_DATA_DIR), prev)


class TestTrackedDataNotDirtiedBySmoke(unittest.TestCase):
    def test_http_smoke_leaves_tracked_world_clean(self):
        world = ROOT / "ssn" / "data" / "world_model.json"
        before = world.read_bytes() if world.exists() else b""
        # Ensure clean git status for world file before
        st = subprocess.run(
            ["git", "status", "--porcelain", "--", "ssn/data/world_model.json"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(st.stdout.strip(), "", msg=st.stdout)
        env = os.environ.copy()
        env["SSN_OFFLINE"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        proc = subprocess.run(
            [str(PY), "scripts/smoke_http.py"],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        after = world.read_bytes() if world.exists() else b""
        self.assertEqual(before, after)
        st2 = subprocess.run(
            ["git", "status", "--porcelain", "--", "ssn/data/world_model.json"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(st2.stdout.strip(), "")

    def test_frontdoor_smoke_leaves_tracked_world_clean(self):
        world = ROOT / "ssn" / "data" / "world_model.json"
        before = world.read_bytes() if world.exists() else b""
        env = os.environ.copy()
        env["SSN_OFFLINE"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env.pop("SSN_MASTER_KEY", None)
        proc = subprocess.run(
            [str(PY), "scripts/smoke_frontdoor.py"],
            cwd=str(ROOT),
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        after = world.read_bytes() if world.exists() else b""
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
