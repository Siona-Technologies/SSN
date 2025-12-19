from ssn.memory.memory_hub import MemoryHub


def run_test():
    mh = MemoryHub()

    # 1. Verify research ingestor exists
    assert hasattr(mh, "research"), "ResearchIngestor not attached to MemoryHub"

    # 2. Ingest sample research
    result = mh.research.ingest(
        title="Test Research",
        content="This is a test knowledge artifact about SSN memory.",
        source="unit_test",
        confidence=0.9,
        metadata={"domain": "architecture"},
    )

    assert result["ok"] is True
    assert result["stored"] is True

    # 3. Verify semantic storage
    stored = mh.recall_fact("research:Test Research")
    assert stored is not None, "Research not found in semantic memory"
    assert stored["confidence"] == 0.9
    assert stored["source"] == "unit_test"

    # 4. Verify trace written
    traces = mh.get_recent_traces(limit=10)
    assert any(t.get("type") == "research_ingest" for t in traces), "No research trace found"

    print("✅ Research ingestion verification PASSED")


if __name__ == "__main__":
    run_test()
