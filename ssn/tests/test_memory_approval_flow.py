import os

from ssn.bootstrap import create_siona
from ssn.tools.research_propose import RESEARCH_PROPOSE_T
from ssn.tools.memory_commit import MEMORY_COMMIT_T
from ssn.tools.memory_propose import MEMORY_PROPOSE_T


def test_memory_approval_flow_offline_owner():
    prev = os.environ.get("SSN_OFFLINE")
    os.environ["SSN_OFFLINE"] = "1"
    try:
        siona = create_siona()

        # Ensure tools are registered for this test run
        siona.tools.register(MEMORY_PROPOSE_T)
        siona.tools.register(MEMORY_COMMIT_T)
        siona.tools.register(RESEARCH_PROPOSE_T)

        # 1) propose
        r = siona.tools.run(
            name="research.propose",
            role="OWNER",
            deps={"tools": siona.tools, "role": "OWNER", "memory": siona.memory},
            args={
                "query": "SIONA SSN hybrid brain system",
                "top_k": 2,
                "max_bytes": 20000,
                "max_answer_chars": 500,
                "max_facts": 3,
                "fact_len": 180,
                "live_search": False,
                "allow_degraded": True,
            },
        )

        assert r.ok is True, r.error
        data = r.data or {}
        pid = data.get("proposal_id")
        assert isinstance(pid, str) and pid.strip()

        # 2) commit (approval required)
        c = siona.tools.run(
            name="memory.commit",
            role="OWNER",
            deps={"tools": siona.tools, "role": "OWNER", "memory": siona.memory},
            args={"proposal_id": pid, "approve": True},
        )

        assert c.ok is True, c.error
        cdata = c.data or {}
        assert cdata.get("committed_count", 0) >= 1

        # 3) proposal must be removed (no replay)
        store = getattr(siona.memory, "_pending_memory_proposals", {})
        assert pid not in store

    finally:
        if prev is None:
            os.environ.pop("SSN_OFFLINE", None)
        else:
            os.environ["SSN_OFFLINE"] = prev
