import math
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
from scipy import stats

from app.models.schemas import (
    AdvancedEDAResult,
    CorrelationPair,
    DataQualityWarning,
    OutlierSummary,
)


class AdvancedEDAEngine:
    """
    Modular Exploratory Data Analysis Engine.
    Provides statistical depth beyond basic profiling:
    - Missingness patterns
    - Correlation rankings with multicollinearity/leakage detection
    - Skewness, kurtosis, and distribution classification
    - IQR & Z-score dual-method outlier detection
    - Automated data quality & target leakage warnings
    - Actionable recommendations
    - Memory-safe sampling for massive datasets
    """

    MAX_COMPUTE_ROWS = 25_000

    @classmethod
    def run_eda(cls, df: pd.DataFrame, dataset_id: str = "") -> AdvancedEDAResult:
        total_rows = len(df)
        sampled = False
        working_df = df

        # Apply computational sampling limit for large datasets
        if total_rows > cls.MAX_COMPUTE_ROWS:
            working_df = df.sample(n=cls.MAX_COMPUTE_ROWS, random_state=42)
            sampled = True

        missingness = cls._analyze_missingness(working_df, total_rows)
        pos_corr, neg_corr, corr_warnings = cls._analyze_correlations(working_df)
        dist_metrics, outliers, outlier_warnings = cls._analyze_distributions_and_outliers(working_df)
        quality_warnings = cls._analyze_quality_warnings(working_df)

        all_warnings = corr_warnings + outlier_warnings + quality_warnings
        recommendations = cls._generate_recommendations(working_df, missingness, all_warnings, pos_corr)

        return AdvancedEDAResult(
            dataset_id=dataset_id,
            sampled=sampled,
            sample_size=len(working_df),
            total_rows=total_rows,
            missingness=missingness,
            top_positive_correlations=pos_corr,
            top_negative_correlations=neg_corr,
            distribution_metrics=dist_metrics,
            outliers=outliers,
            quality_warnings=all_warnings,
            recommendations=recommendations,
        )

    @classmethod
    def _analyze_missingness(cls, df: pd.DataFrame, total_rows: int) -> Dict[str, Any]:
        null_counts = df.isnull().sum()
        total_cells = df.size
        total_missing = int(null_counts.sum())
        missing_pct = round((total_missing / total_cells) * 100, 2) if total_cells > 0 else 0.0

        cols_with_nulls = {}
        for col, count in null_counts[null_counts > 0].items():
            cols_with_nulls[col] = {
                "null_count": int(count),
                "null_percentage": round((count / len(df)) * 100, 2),
            }

        return {
            "total_missing_cells": total_missing,
            "overall_missing_percentage": missing_pct,
            "columns_with_missing_values": cols_with_nulls,
            "complete_rows_count": int(df.dropna().shape[0]),
            "complete_rows_percentage": round((df.dropna().shape[0] / len(df)) * 100, 2) if len(df) > 0 else 0.0,
        }

    @classmethod
    def _analyze_correlations(
        cls, df: pd.DataFrame
    ) -> Tuple[List[CorrelationPair], List[CorrelationPair], List[DataQualityWarning]]:
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        pos_pairs: List[CorrelationPair] = []
        neg_pairs: List[CorrelationPair] = []
        warnings: List[DataQualityWarning] = []

        if len(num_cols) < 2:
            return pos_pairs, neg_pairs, warnings

        corr_matrix = df[num_cols].corr()

        seen = set()
        all_pairs = []

        for c1 in num_cols:
            for c2 in num_cols:
                if c1 == c2:
                    continue
                pair_key = tuple(sorted([c1, c2]))
                if pair_key in seen:
                    continue
                seen.add(pair_key)

                val = corr_matrix.loc[c1, c2]
                if pd.isna(val):
                    continue

                val = float(val)
                abs_val = abs(val)

                if abs_val >= 0.8:
                    strength = "very_strong"
                elif abs_val >= 0.6:
                    strength = "strong"
                elif abs_val >= 0.3:
                    strength = "moderate"
                else:
                    strength = "weak"

                pair_obj = CorrelationPair(
                    col1=pair_key[0],
                    col2=pair_key[1],
                    correlation=round(val, 3),
                    strength=strength,
                )
                all_pairs.append(pair_obj)

                # Check for multicollinearity / potential data leakage
                if abs_val >= 0.98:
                    warnings.append(
                        DataQualityWarning(
                            warning_type="potential_leakage",
                            column=f"{pair_key[0]} & {pair_key[1]}",
                            description=(
                                f"Extremely high correlation ({round(val, 3)}) between '{pair_key[0]}' "
                                f"and '{pair_key[1]}'. May indicate redundant features or data leakage."
                            ),
                            severity="high",
                        )
                    )

        # Sort positive and negative
        pos_sorted = sorted([p for p in all_pairs if p.correlation > 0], key=lambda x: x.correlation, reverse=True)
        neg_sorted = sorted([p for p in all_pairs if p.correlation < 0], key=lambda x: x.correlation)

        return pos_sorted[:5], neg_sorted[:5], warnings

    @classmethod
    def _analyze_distributions_and_outliers(
        cls, df: pd.DataFrame
    ) -> Tuple[Dict[str, Dict[str, Any]], List[OutlierSummary], List[DataQualityWarning]]:
        num_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        dist_metrics: Dict[str, Dict[str, Any]] = {}
        outlier_summaries: List[OutlierSummary] = []
        warnings: List[DataQualityWarning] = []

        for col in num_cols:
            series = df[col].dropna()
            if len(series) < 5:
                continue

            # Distribution moments
            skew = float(series.skew()) if not pd.isna(series.skew()) else 0.0
            kurt = float(series.kurtosis()) if not pd.isna(series.kurtosis()) else 0.0

            if abs(skew) < 0.5:
                shape = "approx_symmetric"
            elif skew > 0.5:
                shape = "right_skewed"
            else:
                shape = "left_skewed"

            dist_metrics[col] = {
                "skewness": round(skew, 3),
                "kurtosis": round(kurt, 3),
                "distribution_shape": shape,
            }

            # Outlier detection (IQR Method)
            q1 = float(series.quantile(0.25))
            q3 = float(series.quantile(0.75))
            iqr = q3 - q1

            if iqr > 0:
                lower_bound = q1 - 1.5 * iqr
                upper_bound = q3 + 1.5 * iqr
                iqr_outliers = series[(series < lower_bound) | (series > upper_bound)]
                iqr_count = len(iqr_outliers)
                iqr_pct = round((iqr_count / len(series)) * 100, 2)
            else:
                lower_bound = q1
                upper_bound = q3
                iqr_count = 0
                iqr_pct = 0.0

            # Outlier detection (Z-score Method)
            std = float(series.std())
            mean = float(series.mean())
            if std > 0:
                zscores = np.abs((series - mean) / std)
                z_outliers = series[zscores > 3.0]
                z_count = len(z_outliers)
                z_pct = round((z_count / len(series)) * 100, 2)
            else:
                z_count = 0
                z_pct = 0.0

            summary = OutlierSummary(
                column=col,
                iqr_outliers_count=iqr_count,
                iqr_outliers_pct=iqr_pct,
                zscore_outliers_count=z_count,
                zscore_outliers_pct=z_pct,
                lower_bound=round(lower_bound, 2),
                upper_bound=round(upper_bound, 2),
            )
            outlier_summaries.append(summary)

            if iqr_pct > 10.0:
                warnings.append(
                    DataQualityWarning(
                        warning_type="high_outliers",
                        column=col,
                        description=(
                            f"Column '{col}' exhibits a high outlier rate ({iqr_pct}% via IQR). "
                            "Consider applying log-transformation or robust scaling."
                        ),
                        severity="medium",
                    )
                )

        return dist_metrics, outlier_summaries, warnings

    @classmethod
    def _analyze_quality_warnings(cls, df: pd.DataFrame) -> List[DataQualityWarning]:
        warnings: List[DataQualityWarning] = []

        # 1. Constant / Zero-variance columns
        for col in df.columns:
            unique_count = df[col].nunique(dropna=False)
            if unique_count == 1:
                warnings.append(
                    DataQualityWarning(
                        warning_type="zero_variance",
                        column=col,
                        description=f"Column '{col}' is constant (contains only 1 unique value) and carries no predictive information.",
                        severity="medium",
                    )
                )
            elif unique_count == len(df) and df[col].dtype == "object":
                warnings.append(
                    DataQualityWarning(
                        warning_type="high_cardinality",
                        column=col,
                        description=f"Text column '{col}' has 100% unique values. Likely an ID, key, or free-text column.",
                        severity="low",
                    )
                )

        # 2. Duplicate rows
        dup_count = int(df.duplicated().sum())
        if dup_count > 0:
            dup_pct = round((dup_count / len(df)) * 100, 2)
            warnings.append(
                DataQualityWarning(
                    warning_type="duplicate_rows",
                    description=f"Dataset contains {dup_count} duplicate rows ({dup_pct}%). Deduplication recommended.",
                    severity="medium" if dup_pct < 10 else "high",
                )
            )

        return warnings

    @classmethod
    def _generate_recommendations(
        cls,
        df: pd.DataFrame,
        missingness: Dict[str, Any],
        warnings: List[DataQualityWarning],
        pos_corrs: List[CorrelationPair],
    ) -> List[str]:
        recs = []

        # Missingness recommendations
        if missingness["overall_missing_percentage"] > 20:
            recs.append(
                f"High overall missingness ({missingness['overall_missing_percentage']}%). "
                "Consider imputation strategies (median for skewed, mode for categorical) or dropping sparsely populated columns."
            )
        elif missingness["overall_missing_percentage"] > 0:
            recs.append("Minor missing values present. Standard median/mean imputation recommended for affected numeric features.")

        # Outlier recommendations
        outlier_warns = [w for w in warnings if w.warning_type == "high_outliers"]
        if outlier_warns:
            cols = [w.column for w in outlier_warns if w.column]
            recs.append(f"Columns {cols} have heavy tails or significant outliers; test non-parametric or tree-based models.")

        # Correlation recommendations
        if pos_corrs:
            top = pos_corrs[0]
            if top.correlation > 0.85:
                recs.append(
                    f"Strong collinearity observed between '{top.col1}' and '{top.col2}' (r={top.correlation}). "
                    "Dimensionality reduction or feature selection recommended before linear modeling."
                )

        # Zero variance
        zero_var = [w for w in warnings if w.warning_type == "zero_variance"]
        if zero_var:
            cols = [w.column for w in zero_var if w.column]
            recs.append(f"Drop constant columns {cols} before downstream modeling.")

        if not recs:
            recs.append("Data quality is exceptionally clean with well-balanced distributions and minimal missing values.")

        return recs
