from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from app.models.schemas import ColumnProfile, DatasetMetadata, DatasetProfile


class ProfilingEngine:
    """
    Deterministic, real-data profiling engine.
    Calculates exact mathematical summaries, detects data quality metrics,
    and infers semantic roles without LLM hallucination.
    """

    @staticmethod
    def infer_semantic_role(col_name: str, series: pd.Series, inferred_type: str) -> str:
        name_lower = col_name.lower()

        # Check target-like indicators
        if any(term in name_lower for term in ["churn", "target", "label", "outcome", "passed", "survived", "fraud"]):
            return "Likely target / outcome"

        # Check identifier
        if inferred_type in ["numeric", "text", "categorical"]:
            if any(term in name_lower for term in ["id", "uuid", "key", "code", "ssn", "isbn"]):
                if series.nunique(dropna=True) / max(len(series), 1) > 0.85:
                    return "Likely identifier"

        # Check datetime
        if inferred_type == "datetime" or any(term in name_lower for term in ["date", "time", "year", "month", "timestamp", "created"]):
            return "Likely datetime / temporal"

        # Check financial / metric
        if inferred_type == "numeric":
            if any(term in name_lower for term in ["price", "cost", "revenue", "profit", "amount", "charge", "sales", "fee", "salary", "balance"]):
                return "Likely financial metric"
            if any(term in name_lower for term in ["age", "hours", "score", "grade", "count", "quantity", "tenure", "rate", "percent"]):
                return "Likely numerical metric"
            return "Likely continuous numeric"

        # Check boolean
        if inferred_type == "boolean":
            return "Likely boolean flag"

        # Check categorical
        if inferred_type == "categorical":
            return "Likely categorical attribute"

        return "Likely text field"

    @classmethod
    def profile_dataframe(cls, df: pd.DataFrame, meta: DatasetMetadata) -> DatasetProfile:
        total_rows = len(df)
        total_cols = len(df.columns)
        total_cells = total_rows * total_cols
        total_missing = int(df.isna().sum().sum())
        missing_pct = round((total_missing / max(total_cells, 1)) * 100, 2)

        duplicate_rows = int(df.duplicated().sum())
        dup_pct = round((duplicate_rows / max(total_rows, 1)) * 100, 2)

        # Calculate a 0-100 data quality score
        quality_score = max(0.0, round(100.0 - (missing_pct * 0.6) - (dup_pct * 0.4), 1))

        column_profiles: List[ColumnProfile] = []

        for col in df.columns:
            series = df[col]
            null_count = int(series.isna().sum())
            col_missing_pct = round((null_count / max(total_rows, 1)) * 100, 2)
            unique_count = int(series.nunique(dropna=True))

            # Sample values (non-null, converted to clean strings or primitives)
            valid_samples = series.dropna().head(5).tolist()
            sample_values = [
                float(x) if isinstance(x, (np.floating, float)) and not np.isnan(x)
                else int(x) if isinstance(x, (np.integer, int))
                else str(x)
                for x in valid_samples
            ]

            # Inferred type classification
            inferred_type = "text"
            min_val, max_val, mean_val, median_val, std_val = None, None, None, None, None
            top_frequencies: Optional[Dict[str, int]] = None
            date_min, date_max = None, None

            # Try datetime first if object/string or datetime64
            is_datetime = False
            if pd.api.types.is_datetime64_any_dtype(series):
                is_datetime = True
            elif pd.api.types.is_string_dtype(series) or series.dtype == "object" or str(series.dtype) in ["string", "str"]:
                # Check sample values to see if parseable as date
                sample_valid = series.dropna().head(20)
                if len(sample_valid) > 0:
                    try:
                        parsed = pd.to_datetime(sample_valid, errors="coerce", format="mixed")
                        if parsed.notna().sum() / len(sample_valid) > 0.8:
                            is_datetime = True
                    except Exception:
                        pass

            if is_datetime:
                inferred_type = "datetime"
                try:
                    dt_series = pd.to_datetime(series, errors="coerce", format="mixed")
                    dt_valid = dt_series.dropna()
                    if len(dt_valid) > 0:
                        date_min = dt_valid.min().isoformat()
                        date_max = dt_valid.max().isoformat()
                except Exception:
                    pass

            elif pd.api.types.is_bool_dtype(series):
                inferred_type = "boolean"
                counts = series.value_counts(dropna=True).head(5).to_dict()
                top_frequencies = {str(k): int(v) for k, v in counts.items()}

            elif pd.api.types.is_numeric_dtype(series):
                inferred_type = "numeric"
                numeric_valid = pd.to_numeric(series, errors="coerce").dropna()
                if len(numeric_valid) > 0:
                    min_val = round(float(numeric_valid.min()), 4)
                    max_val = round(float(numeric_valid.max()), 4)
                    mean_val = round(float(numeric_valid.mean()), 4)
                    median_val = round(float(numeric_valid.median()), 4)
                    std_val = round(float(numeric_valid.std()), 4) if len(numeric_valid) > 1 else 0.0

            else:
                # Text or categorical
                if unique_count <= 25 or (unique_count / max(total_rows, 1) < 0.2):
                    inferred_type = "categorical"
                    counts = series.value_counts(dropna=True).head(10).to_dict()
                    top_frequencies = {str(k): int(v) for k, v in counts.items()}
                else:
                    inferred_type = "text"

            semantic_role = cls.infer_semantic_role(col, series, inferred_type)

            column_profiles.append(
                ColumnProfile(
                    name=str(col),
                    inferred_type=inferred_type,
                    semantic_role=semantic_role,
                    null_count=null_count,
                    null_percentage=col_missing_pct,
                    unique_count=unique_count,
                    sample_values=sample_values,
                    min_val=min_val,
                    max_val=max_val,
                    mean_val=mean_val,
                    median_val=median_val,
                    std_val=std_val,
                    top_frequencies=top_frequencies,
                    date_min=date_min,
                    date_max=date_max,
                )
            )

        # Generate preview rows (first 10 rows, serialized safely)
        preview_df = df.head(10).replace({np.nan: None})
        preview_rows = preview_df.to_dict(orient="records")
        # Ensure clean json serializable types
        clean_preview: List[Dict[str, Any]] = []
        for r in preview_rows:
            clean_row = {}
            for k, v in r.items():
                if isinstance(v, (np.integer, int)):
                    clean_row[str(k)] = int(v)
                elif isinstance(v, (np.floating, float)):
                    clean_row[str(k)] = None if np.isnan(v) else round(float(v), 4)
                elif isinstance(v, (pd.Timestamp, np.datetime64)):
                    clean_row[str(k)] = str(v)
                else:
                    clean_row[str(k)] = v
            clean_preview.append(clean_row)

        return DatasetProfile(
            dataset_id=meta.id,
            metadata=meta,
            columns=column_profiles,
            total_cells=total_cells,
            total_missing_cells=total_missing,
            missing_cells_percentage=missing_pct,
            duplicate_rows=duplicate_rows,
            data_quality_score=quality_score,
            preview_rows=clean_preview,
        )

    @classmethod
    def profile_file(cls, path: Path, meta: DatasetMetadata) -> DatasetProfile:
        file_ext = meta.file_type.lower()
        if file_ext == "csv":
            df = pd.read_csv(path)
        elif file_ext in ["xlsx", "xls"]:
            df = pd.read_excel(path)
        elif file_ext == "json":
            df = pd.read_json(path)
        else:
            raise ValueError(f"Unsupported file format: {file_ext}")

        return cls.profile_dataframe(df, meta)
