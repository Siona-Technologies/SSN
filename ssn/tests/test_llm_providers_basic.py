import os

from ssn.core.llm_providers import (
    LocalDummyLLMProvider,
    HttpLLMProvider,
    LLMRequest,
    get_default_provider_from_env,
)


def test_local_dummy_provider_owner_and_guest():
    prov = LocalDummyLLMProvider()

    owner_resp = prov.generate(LLMRequest(prompt="hello", role="OWNER", context={"x": 1}))
    assert "Samson" in owner_resp.text
    assert owner_resp.meta["role"] == "OWNER"
    assert owner_resp.meta["used_context"] is True

    guest_resp = prov.generate(LLMRequest(prompt="hello", role="GUEST", context=None))
    assert "Guest" in guest_resp.text
    assert guest_resp.meta["role"] == "GUEST"
    assert guest_resp.meta["used_context"] is False


def test_get_default_provider_env_switches_between_dummy_and_http(monkeypatch):
    # Default -> dummy
    monkeypatch.delenv("SSN_LLM_PROVIDER", raising=False)
    p1 = get_default_provider_from_env()
    assert isinstance(p1, LocalDummyLLMProvider)

    # Explicit http -> HttpLLMProvider
    monkeypatch.setenv("SSN_LLM_PROVIDER", "http")
    p2 = get_default_provider_from_env()
    assert isinstance(p2, HttpLLMProvider)


def test_http_provider_falls_back_when_no_endpoint(monkeypatch):
    monkeypatch.delenv("SSN_LLM_ENDPOINT", raising=False)
    prov = HttpLLMProvider(base_url="")

    resp = prov.generate(LLMRequest(prompt="test", role="OWNER", context={"a": 1}))
    assert "[SSN HTTP LLM Stub]" in resp.text
    assert resp.meta["fallback_reason"].startswith("no endpoint configured")
