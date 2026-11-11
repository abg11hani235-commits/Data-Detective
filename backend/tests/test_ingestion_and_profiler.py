import pandas as pd
import numpy as np
import pytest
from app.models.schemas import DatasetMetadata
from app.profiler.engine import ProfilingEngine


def test_profiler_statistics_accuracy():
    # Construct known DataFrame
    df = pd.DataFrame({
        "revenue": [100.0, 200.0, 300.0, 400.0, np.nan],
        "category": ["A", "B", "A", "B", "C"],
        "is_active": [True, False, True, True, False],
        "date": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04", "2025-01-05"]
    })
    meta = DatasetMetadata(
        id="test-meta-1",
        filename="test.csv",
        file_type="csv",
        row_count=5,
        column_count=4,
        file_size_bytes=1024,
        created_at="2026-09-30T12:00:00Z"
    )

    profile = ProfilingEngine.profile_dataframe(df, meta)

    assert profile.metadata.row_count == 5
    assert profile.metadata.column_count == 4
    assert profile.total_cells == 20
    assert profile.total_missing_cells == 1
    assert profile.missing_cells_percentage == 5.0
    assert profile.duplicate_rows == 0

    col_dict = {c.name: c for c in profile.columns}

    # Revenue column
    rev_col = col_dict["revenue"]
    assert rev_col.inferred_type == "numeric"
    assert "metric" in rev_col.semantic_role.lower()
    assert rev_col.null_count == 1
    assert rev_col.min_val == 100.0
    assert rev_col.max_val == 400.0
    assert rev_col.mean_val == 250.0

    # Category column
    cat_col = col_dict["category"]
    assert cat_col.inferred_type == "categorical"
    assert cat_col.null_count == 0
    assert cat_col.unique_count == 3
    assert cat_col.top_frequencies["A"] == 2

    # Date column
    date_col = col_dict["date"]
    assert date_col.inferred_type == "datetime"
    assert "datetime" in date_col.semantic_role.lower()
    assert date_col.date_min is not None


import io
from starlette.datastructures import UploadFile
from fastapi import HTTPException
from app.ingestion.service import IngestionService
from app.config import settings
from app.storage.service import storage


@pytest.mark.asyncio
async def test_upload_empty_file_rejected():
    f = UploadFile(filename="empty.csv", file=io.BytesIO(b""))
    with pytest.raises(HTTPException) as exc_info:
        await IngestionService.process_upload(f)
    assert exc_info.value.status_code == 400
    assert "empty" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_upload_unsupported_format_rejected():
    f = UploadFile(filename="test.exe", file=io.BytesIO(b"binary data"))
    with pytest.raises(HTTPException) as exc_info:
        await IngestionService.process_upload(f)
    assert exc_info.value.status_code == 400
    assert "unsupported" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_upload_size_limit_rejected(monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)  # 1 MB
    oversized_data = b"x" * (1024 * 1024 + 1024)  # 1 MB + 1 KB
    f = UploadFile(filename="huge.csv", file=io.BytesIO(oversized_data))
    with pytest.raises(HTTPException) as exc_info:
        await IngestionService.process_upload(f)
    assert exc_info.value.status_code == 413


@pytest.mark.asyncio
async def test_upload_row_limit_enforced_no_orphaned_file(monkeypatch):
    monkeypatch.setattr(settings, "MAX_DATASET_ROWS", 5)
    csv_content = "id,val\n" + "\n".join(f"{i},{i*10}" for i in range(10))  # 10 rows > 5 cap
    f = UploadFile(filename="too_many_rows.csv", file=io.BytesIO(csv_content.encode("utf-8")))

    initial_files = set(settings.UPLOADS_DIR.glob("*"))
    with pytest.raises(HTTPException) as exc_info:
        await IngestionService.process_upload(f)
    assert exc_info.value.status_code == 400
    assert "row count" in exc_info.value.detail.lower()

    # Verify no new orphaned file was left on disk
    current_files = set(settings.UPLOADS_DIR.glob("*"))
    assert current_files == initial_files


@pytest.mark.asyncio
async def test_upload_column_limit_enforced_no_orphaned_file(monkeypatch):
    monkeypatch.setattr(settings, "MAX_DATASET_COLS", 3)
    header = ",".join(f"col_{i}" for i in range(5))  # 5 columns > 3 cap
    csv_content = f"{header}\n1,2,3,4,5\n"
    f = UploadFile(filename="too_many_cols.csv", file=io.BytesIO(csv_content.encode("utf-8")))

    initial_files = set(settings.UPLOADS_DIR.glob("*"))
    with pytest.raises(HTTPException) as exc_info:
        await IngestionService.process_upload(f)
    assert exc_info.value.status_code == 400
    assert "column count" in exc_info.value.detail.lower()

    # Verify no new orphaned file was left on disk
    current_files = set(settings.UPLOADS_DIR.glob("*"))
    assert current_files == initial_files


@pytest.mark.asyncio
async def test_upload_corrupted_file_no_orphaned_file():
    corrupted_data = b"This is not a valid JSON structure at all: {foo: bar"
    f = UploadFile(filename="corrupt.json", file=io.BytesIO(corrupted_data))

    initial_files = set(settings.UPLOADS_DIR.glob("*"))
    with pytest.raises(HTTPException) as exc_info:
        await IngestionService.process_upload(f)
    assert exc_info.value.status_code == 422

    # Verify no new orphaned file was left on disk
    current_files = set(settings.UPLOADS_DIR.glob("*"))
    assert current_files == initial_files


@pytest.mark.asyncio
async def test_successful_upload_and_profiling():
    csv_content = "item,price,created_at\nLaptop,1200.50,2025-01-01\nMouse,25.00,2025-01-02\n"
    f = UploadFile(filename="valid.csv", file=io.BytesIO(csv_content.encode("utf-8")))

    meta, profile = await IngestionService.process_upload(f)
    assert meta.id is not None
    assert meta.row_count == 2
    assert meta.column_count == 3
    assert profile.dataset_id == meta.id
    assert len(profile.columns) == 3

    # Clean up after test
    storage.remove_dataset(meta.id)

