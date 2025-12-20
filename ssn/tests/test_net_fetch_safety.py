from ssn.bootstrap import create_siona


def test_net_fetch_blocks_localhost_and_private_ips():
    siona = create_siona()

    r1 = siona.run(
        master_key="VALID_OWNER_KEY",
        user_input="fetch localhost",
        context={"force_tool_call": {"name": "net.fetch", "args": {"url": "http://localhost:8000"}}},
    )
    assert r1["allowed"] is True
    assert r1["tool_result"]["ok"] is False
    assert r1["tool_result"]["error"]["code"] in ("SSRF_BLOCKED", "UNSAFE_URL", "DNS_FAILED")

    r2 = siona.run(
        master_key="VALID_OWNER_KEY",
        user_input="fetch loopback",
        context={"force_tool_call": {"name": "net.fetch", "args": {"url": "http://127.0.0.1"}}},
    )
    assert r2["allowed"] is True
    assert r2["tool_result"]["ok"] is False
    assert r2["tool_result"]["error"]["code"] in ("SSRF_BLOCKED", "UNSAFE_URL", "DNS_FAILED")
