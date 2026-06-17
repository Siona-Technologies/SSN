# ssn/tests/test_phase3_tenant_law.py

import os
import tempfile
import unittest

from ssn.policy.policy_engine import PolicyEngine
from ssn.runtime.tenant_config import load_tenant_config, tenant_state_dir


class TestPhase3TenantLaw(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        cls.samson_home = os.path.join(cls.repo_root, "ssn", "policy", "home_law_samson.yaml")
        cls.org_home = os.path.join(cls.repo_root, "deploy", "tenant.example", "home_law_org.yaml")
        cls.world = os.path.join(cls.repo_root, "ssn", "policy", "world_law.yaml")
        cls.system = os.path.join(cls.repo_root, "ssn", "policy", "system_law.yaml")

    def test_samson_owner_ultimate_allows_privileged_action(self) -> None:
        engine = PolicyEngine(
            home_law_path_override=self.samson_home,
            world_law_path_override=self.world,
            system_law_path_override=self.system,
        )
        result = engine.validate_action("OWNER", "unlock_secret_vault")
        self.assertEqual(result["status"], "allow")

    def test_org_bounded_owner_denies_vault_unlock(self) -> None:
        engine = PolicyEngine(
            home_law_path_override=self.org_home,
            world_law_path_override=self.world,
            system_law_path_override=self.system,
        )
        result = engine.validate_action("OWNER", "unlock_secret_vault")
        self.assertEqual(result["status"], "deny")

    def test_org_bounded_owner_allows_interact(self) -> None:
        engine = PolicyEngine(
            home_law_path_override=self.org_home,
            world_law_path_override=self.world,
            system_law_path_override=self.system,
        )
        result = engine.validate_action("OWNER", "interact")
        self.assertEqual(result["status"], "allow")

    def test_org_guest_allowlist_permits_public_tools_action(self) -> None:
        engine = PolicyEngine(
            home_law_path_override=self.org_home,
            world_law_path_override=self.world,
            system_law_path_override=self.system,
        )
        result = engine.validate_action("GUEST", "tools.public_list")
        self.assertEqual(result["status"], "allow")

    def test_samson_guest_still_requires_interact_for_basic_chat(self) -> None:
        engine = PolicyEngine(
            home_law_path_override=self.samson_home,
            world_law_path_override=self.world,
            system_law_path_override=self.system,
        )
        result = engine.validate_action("GUEST", "interact")
        self.assertEqual(result["status"], "allow")

    def test_env_law_paths_resolve(self) -> None:
        prev = os.environ.get("SSN_HOME_LAW_PATH")
        try:
            os.environ["SSN_HOME_LAW_PATH"] = self.org_home
            engine = PolicyEngine()
            self.assertEqual(os.path.abspath(engine.home_law_path), os.path.abspath(self.org_home))
        finally:
            if prev is None:
                os.environ.pop("SSN_HOME_LAW_PATH", None)
            else:
                os.environ["SSN_HOME_LAW_PATH"] = prev

    def test_tenant_state_dir_isolation(self) -> None:
        tmp = tempfile.mkdtemp(prefix="siona_tenant_")
        try:
            d1 = tenant_state_dir(tmp, "org-a")
            d2 = tenant_state_dir(tmp, "org-b")
            self.assertNotEqual(d1, d2)
            self.assertTrue(d1.endswith(os.path.join("tenants", "org-a")))
        finally:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)

    def test_load_tenant_config(self) -> None:
        cfg = load_tenant_config(tenant_id="demo-org", base_state_dir=".ssn_state")
        self.assertEqual(cfg.tenant_id, "demo-org")
        self.assertIn("tenants/demo-org", cfg.state_dir.replace("\\", "/"))


if __name__ == "__main__":
    unittest.main()
