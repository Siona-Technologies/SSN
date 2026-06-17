# ssn/tests/test_net_cite_basic.py

from ssn.bootstrap import create_siona
from ssn.tools.net_cite import NET_CITE_T



if __name__ == "__main__":
    def test_net_cite_owner_allowed():
        siona = create_siona()
        siona.tools.register(NET_CITE_T)

        clean = " ".join(["This is a clean sentence."] * 50)  # deterministic long text

        response = siona.run(
            master_key="VALID_OWNER_KEY",
            user_input="cite this",
            context={
                "force_tool_call": {
                    "name": "net.cite",
                    "args": {
                        "url": "https://example.com/page",
                        "clean_text": clean,
                        "max_quotes": 3,
                        "quote_len": 120,
                    },
                }
            },
        )

        assert response["allowed"] is True
        assert response["role"] == "OWNER"

        tool = response["tool_result"]
        assert tool["ok"] is True

        data = tool["data"]
        assert data["url"] == "https://example.com/page"
        assert data["citation_count"] == 3
        assert isinstance(data["citations"], list) and len(data["citations"]) == 3

        c0 = data["citations"][0]
        assert c0["url"] == "https://example.com/page"
        assert isinstance(c0["quote"], str) and c0["quote"]
        assert isinstance(c0["start"], int)
        assert isinstance(c0["end"], int)
        assert "captured_at" in c0


    def test_net_cite_guest_blocked():
        siona = create_siona()
        siona.tools.register(NET_CITE_T)

        response = siona.run(
            master_key="INVALID_GUEST_KEY",
            user_input="cite this",
            context={
                "force_tool_call": {
                    "name": "net.cite",
                    "args": {
                        "url": "https://example.com/page",
                        "clean_text": "hello world",
                    },
                }
            },
        )

        assert response["allowed"] is False
        assert response["role"] == "GUEST"
