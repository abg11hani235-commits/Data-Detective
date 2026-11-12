import pytest
import io
import uuid
from pathlib import Path
from fastapi import UploadFile

from app.ingestion.service import IngestionService
from app.models.schemas import (
    AnalysisInsights,
    AnalysisResponse,
    DatasetMetadata,
    DatasetProfile,
)
from app.storage.service import storage


@pytest.mark.asyncio
async def test_dataset_and_profile_persistence():
    # 1. Upload a dataset
    csv_bytes = b"category,amount,quantity\nAlpha,100,5\nBeta,200,10\nGamma,300,15\n"
    upload = UploadFile(filename="persistence_test.csv", file=io.BytesIO(csv_bytes))

    meta, profile = await IngestionService.process_upload(upload)
    assert meta.id is not None
    assert meta.row_count == 3
    assert profile.dataset_id == meta.id

    # 2. Clear in-memory caches to simulate server restart
    original_meta = storage.datasets_meta.pop(meta.id)
    original_profile = storage.datasets_profile.pop(meta.id)
    storage.dataset_paths.pop(meta.id)

    assert storage.get_dataset_meta(meta.id) is None
    assert storage.get_dataset_profile(meta.id) is None

    # 3. Reload from database
    await storage.load_all_from_db()

    # 4. Verify data is completely restored
    restored_meta = storage.get_dataset_meta(meta.id)
    restored_profile = storage.get_dataset_profile(meta.id)
    restored_path = storage.get_dataset_path(meta.id)

    assert restored_meta is not None
    assert restored_meta.id == meta.id
    assert restored_meta.filename == "persistence_test.csv"
    assert restored_meta.row_count == 3
    assert restored_profile is not None
    assert restored_profile.dataset_id == meta.id
    assert len(restored_profile.columns) == 3
    assert restored_path is not None
    assert restored_path.exists()

    # 5. Cleanup
    storage.remove_dataset(meta.id)
    assert storage.get_dataset_meta(meta.id) is None


@pytest.mark.asyncio
async def test_session_and_analysis_persistence():
    # 1. Create a session
    sess_resp = await storage.create_session_async(title="Financial Q3 Audit")
    session_id = sess_resp.session_id

    # 2. Add an analysis record to the session
    analysis_id = str(uuid.uuid4())
    analysis = AnalysisResponse(
        id=analysis_id,
        session_id=session_id,
        question="What is the net profit margin?",
        plan="Calculate profit / revenue * 100",
        generated_code="margin = profit / revenue * 100",
        execution_status="success",
        metrics={"margin": 24.5},
        tables=[{"metric": "margin", "value": "24.5%"}],
        charts=[{"data": [1, 2, 3]}],
        insights=AnalysisInsights(
            findings=["Margin is 24.5%"],
            interpretation="Strong profitability",
            caveats=["Q3 seasonal spike"],
        ),
        warnings=[],
        provider_used="groq",
        execution_duration_ms=412.5,
        timestamp="2026-11-12 00:00:00 UTC",
    )
    await storage.add_analysis_async(analysis)

    # 3. Clear memory caches to simulate process restart
    storage.sessions.pop(session_id)
    storage.analyses.pop(analysis_id)

    assert storage.get_session(session_id) is None
    assert storage.get_analysis(analysis_id) is None

    # 4. Reload from DB
    await storage.load_all_from_db()

    # 5. Verify restored state
    restored_session = storage.get_session(session_id)
    restored_analysis = storage.get_analysis(analysis_id)

    assert restored_session is not None
    assert restored_session["session_id"] == session_id
    assert restored_session["title"] == "Financial Q3 Audit"
    assert len(restored_session["history"]) == 1
    assert restored_session["history"][0]["id"] == analysis_id

    assert restored_analysis is not None
    assert restored_analysis.id == analysis_id
    assert restored_analysis.metrics["margin"] == 24.5
    assert restored_analysis.insights.interpretation == "Strong profitability"
