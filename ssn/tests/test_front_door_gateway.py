import unittest

from ssn.interfaces.front_door import handle_user_message
from ssn.tools.contracts import ToolSpec, ToolResult


class FakePolicy:
    def check_permission(self, role: str, action: str) -> bool:
        return True


class FakeTools:
    def __init__(self):
        self._specs = {
            "knowledge.search": ToolSpec(name="knowledge.search", description="x", required_role="OWNER", allowed_roles=("OWNER",), state_changing=False, external_effect=False),
            "knowledge.promote": ToolSpec(name="knowledge.promote", description="x", required_role="OWNER", allowed_roles=("OWNER",), state_changing=True, external_effect=False),
            "research.answer": ToolSpec(name="research.answer", description="x", required_role="OWNER", allowed_roles=("OWNER",), state_changing=False, external_effect=True),
        }

    def get(self, name: str):
        return self._specs.get(name)

    def run(self, *, name: str, role: str, deps: dict, args: dict):
        if name == "knowledge.search":
            if role != "OWNER":
                return ToolResult(ok=False, tool=name, role=role, error={"code": "FORBIDDEN"})
            return ToolResult(ok=True, tool=name, role=role, data={"results": [{"snippet": "KB hit"}], "note": "ok"})
        if name == "knowledge.promote":
            if role != "OWNER":
                return ToolResult(ok=False, tool=name, role=role, error={"code": "FORBIDDEN"})
            return ToolResult(ok=True, tool=name, role=role, data={"kid": "k1", "status": "ok", "note": "ok"})
        if name == "research.answer":
            if role != "OWNER":
                return ToolResult(ok=False, tool=name, role=role, error={"code": "FORBIDDEN"})
            return ToolResult(ok=True, tool=name, role=role, data={"answer": "Research hit", "citations": [{"url": "x"}], "sources": [{"url": "x"}], "degraded": False, "note": "ok"})
        return ToolResult(ok=False, tool=name, role=role, error={"code": "TOOL_NOT_FOUND"})


class FakeOrchestrator:
    def __init__(self):
        self.policy = FakePolicy()
        self.tools = FakeTools()

    def resolve_identity(self, master_key):
        if master_key == "OK":
            return True, "OWNER", {"mock": 1}
        return False, "GUEST", {"mock": 0}

    def call_tool(self, *, name: str, role: str, args=None, context=None):
        tr = self.tools.run(name=name, role=role, deps={"role": role, "tools": self.tools}, args=args or {})
        return {"ok": tr.ok, "tool": tr.tool, "role": tr.role, "data": tr.data, "error": tr.error}

    def llm_route(self, *, role: str, user_input, context=None):
        return {"result": {"fusion": {"final_message": "LLM response"}}}


class TestFrontDoor(unittest.TestCase):
    def setUp(self):
        self.orch = FakeOrchestrator()
        self.deps = {"orchestrator": self.orch}

    def test_kb_search_owner_only(self):
        out_guest = handle_user_message("knowledge: X", self.deps, {"master_key": None})
        self.assertIn("failed", out_guest["answer"].lower())

        out_owner = handle_user_message("knowledge: X", self.deps, {"master_key": "OK"})
        self.assertEqual(out_owner["answer"], "KB hit")
        self.assertEqual(out_owner["used_tools"], ["knowledge.search"])

    def test_promote_owner(self):
        out = handle_user_message("promote: hello", self.deps, {"master_key": "OK"})
        self.assertIn("Knowledge promoted", out["answer"])
        self.assertEqual(out["used_tools"], ["knowledge.promote"])

    def test_research_offline_block(self):
        out = handle_user_message("what is X?", self.deps, {"master_key": "OK", "offline": True})
        self.assertTrue(out["degraded"])
        self.assertEqual(out.get("used_tools", []), [])

    def test_llm_only(self):
        out = handle_user_message("hello", self.deps, {"master_key": None, "allow_tools": False})
        self.assertEqual(out["answer"], "LLM response")


if __name__ == "__main__":
    unittest.main()
