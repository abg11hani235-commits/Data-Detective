from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DatasetMetadata(BaseModel):
    id: str
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


class AnalysisInsights(BaseModel):
    findings: List[str] = Field(default_factory=list)
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
