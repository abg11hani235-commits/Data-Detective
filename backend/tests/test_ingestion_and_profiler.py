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
