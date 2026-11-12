from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DatasetMetadata(BaseModel):
    id: str
    user_id: Optional[str] = None
    filename: str
    file_type: str
    row_count: int
    column_count: int
    file_size_bytes: int
    created_at: str


class ColumnProfile(BaseModel):
    name: str
    inferred_type: str
    semantic_role: str
    null_count: int
    null_percentage: float
    unique_count: int
    sample_values: List[Any] = Field(default_factory=list)
    min_val: Optional[float] = None
    max_val: Optional[float] = None
    mean_val: Optional[float] = None
    median_val: Optional[float] = None
    std_val: Optional[float] = None
    top_frequencies: Optional[Dict[str, int]] = None
    date_min: Optional[str] = None
    date_max: Optional[str] = None


class DatasetProfile(BaseModel):
    dataset_id: str
    metadata: DatasetMetadata
    columns: List[ColumnProfile]
    total_cells: int
    total_missing_cells: int
    missing_cells_percentage: float
    duplicate_rows: int
    data_quality_score: float
    preview_rows: List[Dict[str, Any]] = Field(default_factory=list)


class SessionCreateRequest(BaseModel):
    dataset_id: Optional[str] = None


class SessionResponse(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    dataset_id: Optional[str] = None
    created_at: str
    history_count: int = 0


class QuestionRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)


class ExecutionOutput(BaseModel):
    status: str
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    charts: List[Dict[str, Any]] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    stdout: Optional[str] = None
    error_message: Optional[str] = None


class EvidenceItem(BaseModel):
    id: str
    source: str
    metric_name: str
    dimension: Optional[str] = None
    entity: Optional[str] = None
    aggregation: Optional[str] = None
    value: float
    raw_repr: str


class Claim(BaseModel):
    id: str
    statement: str
    metric_name: str
    dimension: Optional[str] = None
    entity: Optional[str] = None
    aggregation: Optional[str] = None
    claimed_value: Optional[float] = None
    comparison_direction: Optional[str] = None
    evidence_id: Optional[str] = None
    validation_status: str = "pending"  # "verified", "unsupported", "context_mismatch", "contradicted", "missing_evidence"
    reason: Optional[str] = None


class AnalysisInsights(BaseModel):
    findings: List[str] = Field(default_factory=list)
    claims: List[Claim] = Field(default_factory=list)
    interpretation: str = ""
    caveats: List[str] = Field(default_factory=list)


class AnalysisResponse(BaseModel):
    id: str
    session_id: str
    question: str
    plan: str
    generated_code: str
    execution_status: str
    metrics: Dict[str, Any] = Field(default_factory=dict)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    charts: List[Dict[str, Any]] = Field(default_factory=list)
    insights: AnalysisInsights
    warnings: List[str] = Field(default_factory=list)
    provider_used: str
    execution_duration_ms: float
    timestamp: str


class StreamEvent(BaseModel):
    event_type: str
    stage: str
    message: str
    payload: Optional[Dict[str, Any]] = None


class SampleDatasetInfo(BaseModel):
    id: str
    title: str
    category: str
    description: str
    filename: str
    row_count: int
    column_count: int
    sample_questions: List[str]


class UserRegisterRequest(BaseModel):
    email: str = Field(..., min_length=5, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)


class UserLoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


class UserResponse(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    is_active: bool
    created_at: str

