import os
import unittest

from ssn.core.llm_providers import (
    HttpLLMProvider,
    LLMRequest,
    LocalDummyLLMProvider,
    get_default_provider_from_env,
)


class TestLLMProvidersBasic(unittest.TestCase):
    def test_local_dummy_provider_owner_and_guest(self) -> None:
        prov = LocalDummyLLMProvider()

        owner_resp = prov.generate(LLMRequest(prompt="hello", role="OWNER", context={"x": 1}))
        self.assertIn("Samson", owner_resp.text)
        self.assertEqual(owner_resp.meta["role"], "OWNER")
        self.assertTrue(owner_resp.meta["used_context"])

        guest_resp = prov.generate(LLMRequest(prompt="hello", role="GUEST", context=None))
        self.assertIn("Guest", guest_resp.text)
        self.assertEqual(guest_resp.meta["role"], "GUEST")
        self.assertFalse(guest_resp.meta["used_context"])

    def test_get_default_provider_env_switches_between_dummy_and_http(self) -> None:
        prev = os.environ.get("SSN_LLM_PROVIDER")
        try:
            os.environ.pop("SSN_LLM_PROVIDER", None)
            p1 = get_default_provider_from_env()
            self.assertIsInstance(p1, LocalDummyLLMProvider)

            os.environ["SSN_LLM_PROVIDER"] = "http"
            p2 = get_default_provider_from_env()
            self.assertIsInstance(p2, HttpLLMProvider)
        finally:
            if prev is None:
                os.environ.pop("SSN_LLM_PROVIDER", None)
            else:
                os.environ["SSN_LLM_PROVIDER"] = prev

    def test_http_provider_falls_back_when_no_endpoint(self) -> None:
        prov = HttpLLMProvider(base_url="")
        resp = prov.generate(LLMRequest(prompt="test", role="OWNER", context={"a": 1}))
        self.assertIn("[SSN HTTP LLM Stub]", resp.text)
        self.assertTrue(str(resp.meta.get("fallback_reason", "")).startswith("no endpoint configured"))


if __name__ == "__main__":
    unittest.main()
