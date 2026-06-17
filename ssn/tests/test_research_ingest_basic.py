# ssn/tests/test_research_ingest_basic.py

import os

from ssn.bootstrap import create_siona
from ssn.tools.research_ingest import RESEARCH_INGEST_T



if __name__ == "__main__":
    def test_research_ingest_owner_allowed():
        prev = os.environ.get("SSN_OFFLINE")
        os.environ["SSN_OFFLINE"] = "1"
        try:
            siona = create_siona()
            siona.tools.register(RESEARCH_INGEST_T)

            response = siona.run(
                master_key="VALID_OWNER_KEY",
                user_input="ingest",
                context={
                    "force_tool_call": {
                        "name": "research.ingest",
                        "args": {
                            "query": "what is siona",
                            "top_k": 2,
                            "max_bytes": 2000,
                            "max_answer_chars": 400,
                            "live_search": False,
                        },
                    }
                },
            )

            assert response["allowed"] is True
            assert response["role"] == "OWNER"

            tool = response["tool_result"]

            # ✅ If it fails, show the underlying error payload in pytest output.
            if tool["ok"] is not True:
                raise AssertionError(f"research.ingest failed: {tool.get('error')}")

            data = tool["data"]
            assert data["query"] == "what is siona"
            assert "answer" in data and isinstance(data["answer"], str) and len(data["answer"]) > 0
            assert "selected_source" in data and isinstance(data["selected_source"], dict)
            assert "fetch" in data and isinstance(data["fetch"], dict)
            assert "cite" in data

        finally:
            if prev is None:
                os.environ.pop("SSN_OFFLINE", None)
            else:
                os.environ["SSN_OFFLINE"] = prev


    def test_research_ingest_guest_blocked():
        siona = create_siona()
        siona.tools.register(RESEARCH_INGEST_T)

        response = siona.run(
            master_key="INVALID_GUEST_KEY",
            user_input="ingest",
            context={
                "force_tool_call": {
                    "name": "research.ingest",
                    "args": {"query": "what is siona"},
                }
            },
        )

        assert response["allowed"] is False
        assert response["role"] == "GUEST"
