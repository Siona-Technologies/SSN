# ssn/tests/test_net_fetch_basic.py

import os

from ssn.bootstrap import create_siona
from ssn.tools.net_fetch import NET_FETCH_T


def test_net_fetch_owner():
    # Force deterministic offline behavior for unit tests
    prev = os.environ.get("SSN_OFFLINE")
    os.environ["SSN_OFFLINE"] = "1"
    try:
        siona = create_siona()
        siona.tools.register(NET_FETCH_T)

        response = siona.run(
            master_key="VALID_OWNER_KEY",
            user_input="fetch something",
            context={
                "force_tool_call": {
                    "name": "net.fetch",
                    "args": {
                        "url": "https://example.com",
                        "max_bytes": 1000,
                    },
                }
            },
        )

        assert response["allowed"] is True
        assert response["role"] == "OWNER"

        tool = response["tool_result"]
        assert tool["ok"] is True
        assert "content" in tool["data"]
        assert tool["data"]["content_type"] == "text/plain"
        assert tool["data"]["content_bytes"] <= 1000

    finally:
        if prev is None:
            os.environ.pop("SSN_OFFLINE", None)
        else:
            os.environ["SSN_OFFLINE"] = prev


def test_net_fetch_guest_blocked():
    siona = create_siona()
    siona.tools.register(NET_FETCH_T)

    response = siona.run(
        master_key="INVALID_GUEST_KEY",
        user_input="fetch something",
        context={
            "force_tool_call": {
                "name": "net.fetch",
                "args": {"url": "https://example.com"},
            }
        },
    )

    assert response["allowed"] is False
    assert response["role"] == "GUEST"
