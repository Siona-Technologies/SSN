# ssn/tests/test_phase45_doc_ingest_tool.py

import unittest

from ssn.interfaces.contracts import InterfaceRequest
from ssn.interfaces.gateway import InterfaceGateway
from ssn.interfaces.tool_bus import ToolBus
from ssn.interfaces.tools_builtin import register_builtin_tools


class DummyPolicyAllow:
    def is_allowed(self, role, action, context=None, meta=None):
        return True


class DummySafetyAllow:
    def allow_internal_reflection(self):
        return True


class DummyMemoryHub:
    def __init__(self):
        self.writes = []

    def add_trace(self, payload=None, **kwargs):
        if payload is None:
            payload = kwargs.get("payload", {})
        self.writes.append(payload)

    def get_recent_traces(self, limit=50):
        # reflect what was written
        return [{"payload": p} for p in self.writes[-limit:]]


class TestPhase45DocIngestTool(unittest.TestCase):

    def _gateway(self):
        bus = ToolBus()
        register_builtin_tools(bus)
        mh = DummyMemoryHub()
        gw = InterfaceGateway(
            policy_engine=DummyPolicyAllow(),
            safety_monitor=DummySafetyAllow(),
            tool_bus=bus,
            memory_hub=mh,
        )
        return gw, mh

    def test_guest_ingest_text_no_trace_write(self):
        gw, mh = self._gateway()
        req = InterfaceRequest(
            action="tool",
            role="GUEST",
            meta={
                "tool_name": "doc.ingest_readonly",
                "format": "text",
                "document": "Line one.\nLine two is important. You must keep laws.\nLine three.",
                "title": "Test Doc",
            },
        )
        resp = gw.handle(req)
        self.assertTrue(resp.ok)
        self.assertIn("summary_bullets", resp.data)
        self.assertIn("citations", resp.data)
        self.assertEqual(resp.data.get("trace_written"), False)
        self.assertEqual(len(mh.writes), 0)

    def test_owner_ingest_writes_bounded_trace(self):
        gw, mh = self._gateway()
        req = InterfaceRequest(
            action="tool",
            role="OWNER",
            meta={
                "tool_name": "doc.ingest_readonly",
                "format": "text",
                "document": "First line.\nSecond line should be summarized.\nThird line.",
                "title": "Owner Doc",
                "max_citations": 5,
            },
        )
        resp = gw.handle(req)
        self.assertTrue(resp.ok)
        self.assertTrue(resp.data.get("trace_written"))
        self.assertGreaterEqual(len(mh.writes), 1)

        written = mh.writes[-1]
        self.assertEqual(written.get("type"), "doc_ingest")
        # Ensure bounded trace: raw document not stored
        self.assertNotIn("document", written)
        self.assertIn("content_hash", written)
        self.assertIn("citations", written)

    def test_html_ingest_extracts_text(self):
        gw, mh = self._gateway()
        html = "<html><body><h1>Title</h1><p>This is a test.</p><a href='x'>link</a></body></html>"
        req = InterfaceRequest(
            action="tool",
            role="OWNER",
            meta={"tool_name": "doc.ingest_readonly", "format": "html", "document": html, "include_links": True},
        )
        resp = gw.handle(req)
        self.assertTrue(resp.ok)
        self.assertIn("citations", resp.data)
        # links optional but should appear here
        self.assertIn("links", resp.data)


if __name__ == "__main__":
    unittest.main()
