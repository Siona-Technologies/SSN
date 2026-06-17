# ssn/tests/test_research_query_basic.py

from ssn.memory.memory_hub import MemoryHub
from ssn.memory.research_query import ResearchQuery



if __name__ == "__main__":
    def run_test():
        hub = MemoryHub()

        # Inject test research
        hub.research.ingest(
            title="Transformer Models",
            content="Transformers use self-attention mechanisms for sequence modeling.",
            source="paper",
            confidence=0.9,
        )

        hub.research.ingest(
            title="Low confidence note",
            content="This is probably wrong.",
            source="web",
            confidence=0.2,
        )

        rq = ResearchQuery(hub)

        results = rq.search(
            "self-attention",
            min_confidence=0.5,
        )

        assert len(results) == 1
        assert results[0]["title"] == "Transformer Models"

        print("✅ Research query basic test PASSED")


    if __name__ == "__main__":
        run_test()

