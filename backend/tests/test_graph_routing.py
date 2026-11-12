import pytest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from app.agent.graph import build_analysis_graph, sanitize_numerical_data
from app.agent.state import AgentState
from app.providers.manager import provider_manager


def test_sanitize_numerical_data():
    raw = {
        "regular_val": 42.0,
        "nan_val": float("nan"),
        "inf_val": float("inf"),
        "nested": {"bad": float("-inf"), "good": 100},
        "items": [1.5, float("nan"), 3.0],
    }
    sanitized = sanitize_numerical_data(raw)
    assert sanitized["regular_val"] == 42.0
    assert sanitized["nan_val"] is None
    assert sanitized["inf_val"] is None
    assert sanitized["nested"]["bad"] is None
    assert sanitized["nested"]["good"] == 100
    assert sanitized["items"] == [1.5, None, 3.0]


@pytest.mark.asyncio
async def test_invalid_dataset_aborts_to_handle_failure():
    """
    If dataset path does not exist, the graph must route directly to handle_failure
    and NEVER execute code or attempt code generation.
    """
    graph = build_analysis_graph()

    state: AgentState = {
        "session_id": "test_sess",
        "dataset_id": "missing_ds",
        "dataset_path": "non_existent_file_path_12345.csv",
        "file_type": "csv",
        "dataset_metadata": {},
        "column_profiles": [],
        "user_question": "What is the average sales?",
        "conversation_context": [],
        "analysis_plan": "",
        "generated_code": "",
        "code_valid": False,
        "execution_status": "pending",
        "execution_result": {},
        "retry_count": 0,
        "max_retries": 2,
        "tables": [],
        "metrics": {},
        "charts": [],
        "insights": {},
        "warnings": [],
        "errors": [],
        "provider_used": "unknown",
        "execution_duration_ms": 0.0,
    }

    final_state = await graph.ainvoke(state)
    assert final_state.get("generated_code") == ""
    assert "does not exist" in final_state.get("errors", [""])[0]
    insights = final_state.get("insights", {})
    assert "The analysis could not complete" in insights.get("findings", [""])[0]


@pytest.mark.asyncio
async def test_malicious_code_blocked_from_execution():
    """
    If generated code contains forbidden AST constructs (e.g. import os),
    the code validator must set code_valid = False and route away from execution.
    """
    graph = build_analysis_graph()

    dummy_csv = Path("backend/data/sandbox_tmp/test_guard.csv")
    dummy_csv.parent.mkdir(parents=True, exist_ok=True)
    dummy_csv.write_text("a,b\n1,2\n")

    state: AgentState = {
        "session_id": "test_sess_sec",
        "dataset_id": "test_ds",
        "dataset_path": str(dummy_csv.resolve()),
        "file_type": "csv",
        "dataset_metadata": {"filename": "test_guard.csv", "row_count": 1, "column_count": 2},
        "column_profiles": [{"name": "a", "inferred_type": "numeric"}, {"name": "b", "inferred_type": "numeric"}],
        "user_question": "Run system command",
        "conversation_context": [],
        "analysis_plan": "Execute command",
        "generated_code": "",
        "code_valid": False,
        "execution_status": "pending",
        "execution_result": {},
        "retry_count": 2,  # At max_retries: if code fails validation, routes directly to handle_failure
        "max_retries": 2,
        "tables": [],
        "metrics": {},
        "charts": [],
        "insights": {},
        "warnings": [],
        "errors": [],
        "provider_used": "mock",
        "execution_duration_ms": 0.0,
    }

    try:
        # Mock generate_with_fallback to return malicious code
        with patch.object(
            provider_manager,
            "generate_with_fallback",
            new_callable=AsyncMock,
            return_value=("import os\nos.system('whoami')", "mock"),
        ):
            final_state = await graph.ainvoke(state)

        # The malicious code must have been flagged and blocked from executing!
        assert final_state.get("code_valid") is False
        assert final_state.get("execution_status") == "security_violation"
        # The execution_result should be empty because execute_python was never entered!
        assert final_state.get("execution_result") == {}
        # Insights must reflect failure
        insights = final_state.get("insights", {})
        assert "The analysis could not complete" in insights.get("findings", [""])[0]
    finally:
        if dummy_csv.exists():
            dummy_csv.unlink()
