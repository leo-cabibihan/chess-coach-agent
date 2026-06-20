from chess_coach_agent.llm import _execute_coach_tools, _parse_tool_plan


def test_tool_plan_requires_multiple_known_tools():
    selected = _parse_tool_plan('{"tools":["build_training_drill","retrieve_principles"]}')
    assert selected == ["build_training_drill", "retrieve_principles"]

    fallback = _parse_tool_plan('{"tools":["unknown"]}')
    assert fallback == ["retrieve_principles", "inspect_critical_moments"]


def test_tool_executor_runs_retrieval_and_position_inspection_without_game():
    observations, titles = _execute_coach_tools(
        ["retrieve_principles", "inspect_critical_moments"],
        "checks captures threats",
        None,
    )
    assert len(observations) == 2
    assert "Tactical Vision" in titles
