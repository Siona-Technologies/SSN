# ssn/tests/test_memory_curation_basic.py

from ssn.bootstrap import create_siona
from ssn.tools.memory_propose import MEMORY_PROPOSE_T
from ssn.tools.memory_commit import MEMORY_COMMIT_T



if __name__ == "__main__":
    def test_memory_propose_and_commit_owner():
        siona = create_siona()
        siona.tools.register(MEMORY_PROPOSE_T)
        siona.tools.register(MEMORY_COMMIT_T)

        # 1) Propose facts
        propose_resp = siona.run(
            master_key="VALID_OWNER_KEY",
            user_input="propose facts",
            context={
                "force_tool_call": {
                    "name": "memory.propose",
                    "args": {
                        "facts": [
                            {"key": "Owner", "value": "Samson Sibona Njaji", "confidence": 1.0},
                            {"key": "System", "value": "SIONA (SSN)", "confidence": 0.9},
                        ]
                    },
                }
            },
        )

        assert propose_resp["allowed"] is True
        assert propose_resp["role"] == "OWNER"
        assert propose_resp["tool_result"]["ok"] is True

        proposal_id = propose_resp["tool_result"]["data"]["proposal_id"]
        assert isinstance(proposal_id, str) and proposal_id

        # 2) Commit facts (explicit approval)
        commit_resp = siona.run(
            master_key="VALID_OWNER_KEY",
            user_input="commit facts",
            context={
                "force_tool_call": {
                    "name": "memory.commit",
                    "args": {
                        "proposal_id": proposal_id,
                        "approve": True,
                    },
                }
            },
        )

        assert commit_resp["allowed"] is True
        assert commit_resp["role"] == "OWNER"
        assert commit_resp["tool_result"]["ok"] is True

        data = commit_resp["tool_result"]["data"]
        assert data["proposal_id"] == proposal_id
        assert data["committed_count"] >= 0
        assert "committed_at" in data


    def test_memory_curation_guest_blocked():
        siona = create_siona()
        siona.tools.register(MEMORY_PROPOSE_T)
        siona.tools.register(MEMORY_COMMIT_T)

        # GUEST propose blocked
        resp1 = siona.run(
            master_key="INVALID_GUEST_KEY",
            user_input="propose facts",
            context={
                "force_tool_call": {
                    "name": "memory.propose",
                    "args": {"facts": [{"key": "x", "value": "y"}]},
                }
            },
        )
        assert resp1["allowed"] is False
        assert resp1["role"] == "GUEST"

        # GUEST commit blocked
        resp2 = siona.run(
            master_key="INVALID_GUEST_KEY",
            user_input="commit facts",
            context={
                "force_tool_call": {
                    "name": "memory.commit",
                    "args": {"proposal_id": "prop_fake", "approve": True},
                }
            },
        )
        assert resp2["allowed"] is False
        assert resp2["role"] == "GUEST"
