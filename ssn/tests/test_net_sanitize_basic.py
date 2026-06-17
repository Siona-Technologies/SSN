from ssn.bootstrap import create_siona
from ssn.tools.net_sanitize import NET_SANITIZE_T



if __name__ == "__main__":
    def test_net_sanitize_owner_allowed():
        siona = create_siona()
        siona.tools.register(NET_SANITIZE_T)

        html = """
        <html>
          <head>
            <style>body{background:red}</style>
            <script>alert("x")</script>
          </head>
          <body>
            <h1>Hello World</h1>
            <p>Some   text.</p>
          </body>
        </html>
        """

        response = siona.run(
            master_key="VALID_OWNER_KEY",
            user_input="sanitize this",
            context={
                "force_tool_call": {
                    "name": "net.sanitize",
                    "args": {
                        "url": "https://example.com/page",
                        "content_type": "text/html",
                        "content": html,
                        "max_bytes": 2000,
                    },
                }
            },
        )

        assert response["allowed"] is True
        assert response["role"] == "OWNER"

        tool = response["tool_result"]
        assert tool["ok"] is True

        data = tool["data"]
        assert data["content_type"] == "text/plain"
        assert isinstance(data["clean_text"], str) and data["clean_text"]
        assert "alert" not in data["clean_text"].lower()
        assert "body{background" not in data["clean_text"].lower()
        assert isinstance(data["clean_bytes"], int) and data["clean_bytes"] > 0
        assert isinstance(data["original_bytes"], int) and data["original_bytes"] > 0
        assert "sanitized_at" in data


    def test_net_sanitize_guest_blocked():
        siona = create_siona()
        siona.tools.register(NET_SANITIZE_T)

        response = siona.run(
            master_key="INVALID_GUEST_KEY",
            user_input="sanitize this",
            context={
                "force_tool_call": {
                    "name": "net.sanitize",
                    "args": {
                        "content_type": "text/plain",
                        "content": "hello",
                    },
                }
            },
        )

        assert response["allowed"] is False
        assert response["role"] == "GUEST"
