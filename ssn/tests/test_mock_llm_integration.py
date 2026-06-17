# ssn/tests/test_mock_llm_integration.py

import json
import os
import threading
import unittest
from urllib import request as urllib_request

from ssn.core.llm_providers import HttpLLMProvider, LLMRequest

from ssn.runtime.mock_llm_server import MockLLMHandler, ThreadingHTTPServer


class TestMockLLMIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._server = ThreadingHTTPServer(("127.0.0.1", 0), MockLLMHandler)
        cls.port = cls._server.server_address[1]
        cls.base_url = f"http://127.0.0.1:{cls.port}/generate"
        cls._thread = threading.Thread(target=cls._server.serve_forever, daemon=True)
        cls._thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        cls._server.shutdown()
        cls._server.server_close()

    def test_http_provider_receives_mock_reply(self) -> None:
        prov = HttpLLMProvider(base_url=self.base_url)
        resp = prov.generate(LLMRequest(prompt="hello integration", role="OWNER", context={"k": 1}))

        self.assertNotIn("[SSN HTTP LLM Stub]", resp.text)
        self.assertIn("[MockLLM OWNER]", resp.text)
        self.assertIn("hello integration", resp.text)
        self.assertEqual(resp.meta.get("engine"), "siona-mock-llm-v1")
        self.assertTrue(resp.meta.get("used_context"))

    def test_mock_server_health(self) -> None:
        url = f"http://127.0.0.1:{self.port}/health"
        with urllib_request.urlopen(url, timeout=5.0) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        self.assertTrue(data.get("ok"))


if __name__ == "__main__":
    unittest.main()
