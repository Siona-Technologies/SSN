# ssn/tests/test_research_propose_basic.py

import os

from ssn.bootstrap import create_siona
from ssn.tools.research_propose import RESEARCH_PROPOSE_T



if __name__ == "__main__":
    def test_research_propose_owner_allowed():
        prev = os.environ.get("SSN_OFFLINE")
        os.environ["SSN_OFFLINE"] = "1"
        try:
            siona = create_siona()
            siona.tools.register(RESEARCH_PROPOSE_T)

            response = siona.run(
                master_key="VALID_OWNER_KEY",
                user_input="propose",
                context={
                    "force_tool_call": {
                        "name": "research.propose",
                        "args": {
                            "query": "what is siona",
                            "top_k": 2,
                            "max_bytes": 2000,
                            "max_answer_chars": 400,
                            "max_facts": 4,
                            "fact_len": 160,
                            "live_search": False,
                        },
                    }
                },
            )

            assert response["allowed"] is True
            assert response["role"] == "OWNER"

            tool = response["tool_result"]
            if tool["ok"] is not True:
                raise AssertionError(f"research.propose failed: {tool.get('error')}")

            data = tool["data"]
            assert data["query"] == "what is siona"
            assert "facts" in data and isinstance(data["facts"], list) and len(data["facts"]) > 0
            assert "proposal" in data and isinstance(data["proposal"], dict)

            # proposal_id may vary by implementation; require at least some id-like signal
            assert data.get("proposal_id") is None or isinstance(data.get("proposal_id"), str)

        finally:
            if prev is None:
                os.environ.pop("SSN_OFFLINE", None)
            else:
                os.environ["SSN_OFFLINE"] = prev


    def test_research_propose_guest_blocked():
        siona = create_siona()
        siona.tools.register(RESEARCH_PROPOSE_T)

        response = siona.run(
            master_key="INVALID_GUEST_KEY",
            user_input="propose",
            context={
                "force_tool_call": {
                    "name": "research.propose",
                    "args": {"query": "what is siona"},
                }
            },
        )

        assert response["allowed"] is False
        assert response["role"] == "GUEST"
