# ssn/tests/test_research_answer_basic.py

import os

from ssn.bootstrap import create_siona
from ssn.tools.research_answer import RESEARCH_ANSWER_T



if __name__ == "__main__":
    def test_research_answer_owner_allowed():
        # Force deterministic offline behavior for unit tests
        prev = os.environ.get("SSN_OFFLINE")
        os.environ["SSN_OFFLINE"] = "1"
        try:
            siona = create_siona()
            siona.tools.register(RESEARCH_ANSWER_T)

            response = siona.run(
                master_key="VALID_OWNER_KEY",
                user_input="answer this",
                context={
                    "force_tool_call": {
                        "name": "research.answer",
                        "args": {
                            "query": "what is siona",
                            "top_k": 2,
                            "max_bytes": 2000,
                            "max_quotes": 2,
                            "quote_len": 120,
                            "max_answer_chars": 400,
                        },
                    }
                },
            )

            assert response["allowed"] is True
            assert response["role"] == "OWNER"

            tool = response["tool_result"]
            assert tool["ok"] is True
            assert "answer" in tool["data"]
            assert isinstance(tool["data"]["answer"], str)
            assert len(tool["data"]["answer"]) > 0

        finally:
            if prev is None:
                os.environ.pop("SSN_OFFLINE", None)
            else:
                os.environ["SSN_OFFLINE"] = prev


    def test_research_answer_guest_blocked():
        siona = create_siona()
        siona.tools.register(RESEARCH_ANSWER_T)

        response = siona.run(
            master_key="INVALID_GUEST_KEY",
            user_input="answer this",
            context={
                "force_tool_call": {
                    "name": "research.answer",
                    "args": {"query": "what is siona"},
                }
            },
        )

        assert response["allowed"] is False
        assert response["role"] == "GUEST"
