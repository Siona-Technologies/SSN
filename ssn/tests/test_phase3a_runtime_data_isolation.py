"""Phase 3A — runtime-data isolation regression tests."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

os.environ.setdefault("SSN_OFFLINE", "1")

ROOT = Path(__file__).resolve().parents[2]
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

        with isolated_runtime_data(prefix="iso-b-") as b:
            wb = WorldModel()
            path_b = wb.path
            self.assertNotEqual(path_a, path_b)
            snap_b = wb.snapshot(max_entities=10, max_events=10)
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
        self.assertEqual(os.environ.get(ENV_RUNTIME_DATA_DIR), prev)

    def test_external_env_restored_and_cleanup_ownership(self):
        from ssn.runtime.paths import (
            ENV_RUNTIME_DATA_DIR,
            cleanup_ensured_isolation,
            ensure_isolated_for_tests,
        )

        external = Path(os.environ.get("TEMP") or os.environ.get("TMP") or ".") / "siona-external-probe"
        external.mkdir(parents=True, exist_ok=True)
        try:
            with mock.patch.dict(
                os.environ,
                {ENV_RUNTIME_DATA_DIR: str(external)},
                clear=False,
            ):
                # Already set externally — ensure must not claim ownership
                self.assertIsNone(ensure_isolated_for_tests())
                cleanup_ensured_isolation()
                self.assertEqual(os.environ.get(ENV_RUNTIME_DATA_DIR), str(external))
        finally:
            pass

    def test_per_test_unique_path_attribute(self):
        # Governed runner sets _ssn_runtime_data_dir; when run standalone may be absent
        path = getattr(self, "_ssn_runtime_data_dir", None)
        if path:
            self.assertTrue(Path(path).exists())

    def test_no_hardcoded_developer_python_path(self):
        # Construct banned fragment without embedding the full literal machine path.
        banned = "Documents" + os.sep + "SSN" + os.sep + ".venv" + os.sep + "Scripts" + os.sep + "python.exe"
        roots = [
            ROOT / "ssn" / "tests",
            ROOT / "ssn" / "runtime",
            ROOT / "ssn" / "cognition" / "model_gateway",
            ROOT / "ssn" / "eval",
        ]
        for root in roots:
            for p in root.glob("*.py"):
                if p.name.startswith("test_phase3a") or root.name in {
                    "runtime",
                    "model_gateway",
                    "eval",
                }:
                    if root.name == "tests" and not p.name.startswith("test_phase3a"):
                        continue
                    body = p.read_text(encoding="utf-8")
                    self.assertNotIn(banned, body, msg=str(p))
                    self.assertNotIn(banned.replace("\\", "/"), body.replace("\\", "/"), msg=str(p))


class TestTrackedDataNotDirtiedBySmoke(unittest.TestCase):
    def test_http_smoke_leaves_tracked_world_clean(self):
        world = ROOT / "ssn" / "data" / "world_model.json"
        before = world.read_bytes() if world.exists() else b""
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

    def test_concurrent_subprocesses_separate_state(self):
        script = r"""
import os, sys
from ssn.runtime.paths import ensure_isolated_for_tests, get_runtime_data_dir
from ssn.world.world_model import WorldModel
ensure_isolated_for_tests()
wm = WorldModel()
wm.apply_update({
    "type":"world_update","ts":1.0,"source":"t","entities":[
        {"id": os.environ.get("MARKER","x"),"entity":"m","status":"present","confidence":1.0,"attributes":{}}
    ],"events":[]
})
print(get_runtime_data_dir())
print(wm.path)
"""
        env_a = os.environ.copy()
        env_a["SSN_OFFLINE"] = "1"
        env_a["MARKER"] = "proc-a"
        env_a.pop("SSN_RUNTIME_DATA_DIR", None)
        env_b = env_a.copy()
        env_b["MARKER"] = "proc-b"
        pa = subprocess.run([str(PY), "-c", script], cwd=str(ROOT), env=env_a, capture_output=True, text=True)
        pb = subprocess.run([str(PY), "-c", script], cwd=str(ROOT), env=env_b, capture_output=True, text=True)
        self.assertEqual(pa.returncode, 0, pa.stderr)
        self.assertEqual(pb.returncode, 0, pb.stderr)
        path_a = pa.stdout.strip().splitlines()[-1]
        path_b = pb.stdout.strip().splitlines()[-1]
        self.assertNotEqual(path_a, path_b)


if __name__ == "__main__":
    unittest.main()
