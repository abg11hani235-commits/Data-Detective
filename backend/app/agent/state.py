from typing import Any, Callable, Dict, List, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict):
    session_id: str
    dataset_id: str
    dataset_path: str
    file_type: str
    dataset_metadata: Dict[str, Any]
    column_profiles: List[Dict[str, Any]]
    user_question: str
    conversation_context: List[Dict[str, Any]]

    # Pipeline progression
    analysis_plan: str
    generated_code: str
    code_valid: bool
    execution_status: str
    execution_result: Dict[str, Any]
    retry_count: int
    max_retries: int

    # Final outputs
    tables: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    charts: List[Dict[str, Any]]
    insights: Dict[str, Any]
    warnings: List[str]
    errors: List[str]
    provider_used: str
    execution_duration_ms: float
