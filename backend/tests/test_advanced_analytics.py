import numpy as np
import pandas as pd
import pytest

from app.analytics.statistics import StatisticalTestingEngine
from app.profiler.advanced_eda import AdvancedEDAEngine


def test_advanced_eda_engine_full_spectrum():
    # Construct a dataset with diverse characteristics:
    # - Known outliers in col 'outlier_col'
    # - Constant column 'const_col'
    # - Highly correlated pair (x and y)
    # - Missing values in 'sparse_col'
    np.random.seed(42)
    n = 200

    x = np.linspace(10, 100, n)
    y = x * 2.0 + np.random.normal(0, 0.1, n)  # Pearson r ~ 0.999 (leakage candidate)
    normal_data = np.random.normal(50, 10, n)

    # Column with heavy outliers
    outliers_data = np.random.normal(10, 2, n)
    outliers_data[0] = 500.0
    outliers_data[1] = 600.0
    outliers_data[2] = 700.0

    sparse_data = [None if i % 4 == 0 else float(i) for i in range(n)]

    df = pd.DataFrame({
        "x": x,
        "y": y,
        "normal_feat": normal_data,
        "outlier_col": outliers_data,
        "const_col": ["Fixed_Value"] * n,
        "sparse_col": sparse_data,
    })

    eda_result = AdvancedEDAEngine.run_eda(df, dataset_id="test_eda_dataset")

    assert eda_result.total_rows == 200
    assert eda_result.sampled is False

    # 1. Missingness checks
    missing = eda_result.missingness
    assert missing["total_missing_cells"] == 50
    assert missing["overall_missing_percentage"] > 0
    assert "sparse_col" in missing["columns_with_missing_values"]

    # 2. Correlation checks
    assert len(eda_result.top_positive_correlations) > 0
    top_pos = eda_result.top_positive_correlations[0]
    assert {top_pos.col1, top_pos.col2} == {"x", "y"}
    assert top_pos.correlation > 0.98

    # 3. Quality warnings (zero variance and potential leakage)
    warning_types = [w.warning_type for w in eda_result.quality_warnings]
    assert "zero_variance" in warning_types
    assert "potential_leakage" in warning_types

    # 4. Outliers
    outlier_cols = {o.column: o for o in eda_result.outliers}
    assert "outlier_col" in outlier_cols
    assert outlier_cols["outlier_col"].iqr_outliers_count >= 3

    # 5. Recommendations
    assert len(eda_result.recommendations) > 0


def test_statistics_normality_test():
    np.random.seed(42)
    # Gaussian distribution -> should be normal
    normal_data = pd.Series(np.random.normal(100, 15, 100))
    res_norm = StatisticalTestingEngine.test_normality(normal_data)
    assert res_norm["is_normal"] is True
    assert res_norm["p_value"] > 0.05

    # Uniform or exponential distribution -> non-normal
    exp_data = pd.Series(np.random.exponential(scale=2.0, size=200))
    res_exp = StatisticalTestingEngine.test_normality(exp_data)
    assert res_exp["is_normal"] is False
    assert res_exp["p_value"] <= 0.05


def test_statistics_two_group_comparison_parametric_and_non_parametric():
    np.random.seed(42)

    # 1. Normal groups with significant difference -> Welch's t-test
    g1 = pd.Series(np.random.normal(50, 5, 50))
    g2 = pd.Series(np.random.normal(65, 5, 50))
    res_param = StatisticalTestingEngine.compare_two_groups(g1, g2, "GroupA", "GroupB")
    assert "t-test" in res_param["test_type"]
    assert res_param["is_significant"] is True
    assert "Cohen's d" in res_param["effect_size"]["metric"]
    assert "causality_caveat" in res_param

    # 2. Skewed / Exponential groups -> Mann-Whitney U test fallback
    g3 = pd.Series(np.random.exponential(1.0, 50))
    g4 = pd.Series(np.random.exponential(5.0, 50))
    res_non_param = StatisticalTestingEngine.compare_two_groups(g3, g4, "ExpA", "ExpB")
    assert "Mann-Whitney" in res_non_param["test_type"]
    assert res_non_param["is_significant"] is True
    assert "Rank-Biserial" in res_non_param["effect_size"]["metric"]
    assert "causality_caveat" in res_param


def test_statistics_categorical_association_chi2():
    # Contingency test: Education level vs Subscription choice
    data = pd.DataFrame({
        "education": ["BS", "BS", "MS", "MS", "PhD", "PhD"] * 20,
        "subscription": ["TierA", "TierB", "TierB", "TierC", "TierC", "TierC"] * 20,
    })
    res = StatisticalTestingEngine.test_categorical_association(data["education"], data["subscription"])
    assert res["test_type"] == "Chi-Square Test of Independence"
    assert res["is_significant"] is True
    assert res["cramers_v"] > 0
    assert "causality_caveat" in res


def test_statistics_correlation_and_causal_caveats():
    np.random.seed(42)
    x = pd.Series(np.linspace(1, 100, 60))
    y = x * 3.5 + pd.Series(np.random.normal(0, 5, 60))

    res = StatisticalTestingEngine.test_correlation(x, y, "Ad Spend", "Conversions")
    assert res["is_significant"] is True
    assert res["correlation_coefficient"] > 0.9
    assert res["direction"] == "positive"
    # Mandatory requirement: correlation does not imply causation must be explicitly included
    assert "Correlation does NOT equal causation" in res["causality_caveat"]
