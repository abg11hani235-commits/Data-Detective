import uuid
from typing import List
from fastapi import APIRouter, HTTPException

from app.config import settings
from app.models.schemas import DatasetProfile, SampleDatasetInfo
from app.profiler.engine import ProfilingEngine
from app.storage.service import storage

router = APIRouter(prefix="/api/samples", tags=["samples"])

SAMPLE_DEFINITIONS = [
    SampleDatasetInfo(
        id="sales",
        title="Global Retail Sales",
        category="Sales & Revenue",
        description="Multi-region sales records covering products, volume, pricing, revenue, costs, and profits.",
        filename="sales.csv",
        row_count=250,
        column_count=9,
        sample_questions=[
            "Which products generated the highest revenue and profit?",
            "How does total revenue compare across different regions?",
            "What is the monthly revenue trend over time?",
            "Which product category has the highest average profit margin?",
            "Is there a relationship between unit price and quantity sold?",
        ],
    ),
    SampleDatasetInfo(
        id="churn",
        title="Telecom Customer Churn",
        category="Customer Analytics",
        description="Customer subscription tenure, monthly charges, contract types, support tickets, and churn labels.",
        filename="customer_churn.csv",
        row_count=200,
        column_count=7,
        sample_questions=[
            "What is the overall churn rate and how does it compare across contract types?",
            "Is there a relationship between support calls and customer churn?",
            "Compare monthly charges between churned and retained customers.",
            "How does customer tenure relate to churn probability?",
            "What is the average age of churned vs non-churned customers?",
        ],
    ),
    SampleDatasetInfo(
        id="students",
        title="Student Academic Performance",
        category="Education & Learning",
        description="Study hours, attendance rates, assignment scores, midterm marks, and final exam grades.",
        filename="student_performance.csv",
        row_count=200,
        column_count=6,
        sample_questions=[
            "What is the correlation between study hours and final score?",
            "Compare the distribution of midterm vs final exam scores.",
            "How does attendance percentage impact final score outcomes?",
            "Who are the top 10 scoring students and what was their attendance rate?",
            "What is the average assignment score compared to final score across study hour quartiles?",
        ],
    ),
]


@router.get("", response_model=List[SampleDatasetInfo])
async def list_sample_datasets():
    return SAMPLE_DEFINITIONS


@router.post("/{sample_id}/load", response_model=DatasetProfile)
async def load_sample_dataset(sample_id: str):
    matched = next((s for s in SAMPLE_DEFINITIONS if s.id == sample_id), None)
    if not matched:
        raise HTTPException(status_code=404, detail=f"Sample dataset '{sample_id}' not found.")

    sample_path = settings.SAMPLES_DIR / matched.filename
    if not sample_path.exists():
        raise HTTPException(status_code=500, detail=f"Sample file '{matched.filename}' missing from disk.")

    dataset_id = f"sample-{sample_id}-{str(uuid.uuid4())[:8]}"
    meta = storage.register_existing_file(
        dataset_id=dataset_id,
        filename=matched.filename,
        path=sample_path,
        file_type="csv",
    )

    profile = ProfilingEngine.profile_file(sample_path, meta)
    storage.save_dataset_profile(profile)

    return profile
