from ssn.bootstrap import create_siona


def test_net_search_owner():
    siona = create_siona()

    response = siona.run(
        master_key="VALID_OWNER_KEY",
        user_input="Search test",
        context={
            "force_tool_call": {
                "name": "net.search",
                "args": {
                    "query": "spiking neural networks",
                    "top_k": 3,
                },
            }
        },
    )

    assert response["allowed"] is True
    assert response["role"] == "OWNER"
    assert response["tool_result"]["ok"] is True

    data = response["tool_result"]["data"]
    assert "results" in data
    assert len(data["results"]) > 0
