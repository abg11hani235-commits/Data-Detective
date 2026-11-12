import math
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from scipy import stats


class StatisticalTestingEngine:
    """
    Principled Statistical Testing Engine.
    Enforces assumption checking before executing parametric tests,
    automatically falls back to non-parametric equivalents when assumptions are violated,
    computes standardized effect sizes, and provides explicit causal caveats.
    """

    @classmethod
    def test_normality(cls, series: pd.Series, alpha: float = 0.05) -> Dict[str, Any]:
        clean = series.dropna().astype(float)
        n = len(clean)

        if n < 8:
            return {
                "test": "Insufficient Data",
                "is_normal": False,
                "reason": f"Sample size {n} is too small for reliable normality testing (minimum 8 required).",
            }

        if n <= 5000:
            stat, p_val = stats.shapiro(clean)
            test_name = "Shapiro-Wilk Normality Test"
        else:
            stat, p_val = stats.normaltest(clean)
            test_name = "D'Agostino and Pearson's omnibus test"

        is_normal = bool(p_val > alpha)

        return {
            "test": test_name,
            "sample_size": n,
            "statistic": round(float(stat), 4),
            "p_value": round(float(p_val), 5),
            "alpha": alpha,
            "is_normal": is_normal,
            "interpretation": (
                f"Data is consistent with a normal distribution (p={round(p_val, 4)} > {alpha})."
                if is_normal
                else f"Data significantly deviates from normality (p={round(p_val, 4)} <= {alpha}). Non-parametric methods recommended."
            ),
            "skewness": round(float(clean.skew()), 3),
            "kurtosis": round(float(clean.kurtosis()), 3),
        }

    @classmethod
    def compare_two_groups(
        cls,
        group1: pd.Series,
        group2: pd.Series,
        group1_name: str = "Group 1",
        group2_name: str = "Group 2",
        alpha: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Compares two independent groups.
        Checks normality first:
        - If normal: executes Welch's t-test (robust against unequal variance) + Cohen's d.
        - If non-normal: executes Mann-Whitney U test + Rank-Biserial effect size.
        """
        g1 = group1.dropna().astype(float)
        g2 = group2.dropna().astype(float)

        if len(g1) < 5 or len(g2) < 5:
            return {
                "error": "Both groups must have at least 5 observations for comparison testing.",
            }

        # Check normality
        norm1 = cls.test_normality(g1, alpha=alpha)
        norm2 = cls.test_normality(g2, alpha=alpha)

        both_normal = norm1.get("is_normal", False) and norm2.get("is_normal", False)

        m1, s1, n1 = float(g1.mean()), float(g1.std()), len(g1)
        m2, s2, n2 = float(g2.mean()), float(g2.std()), len(g2)

        if both_normal:
            # Welch's t-test (equal_var=False)
            t_res = stats.ttest_ind(g1, g2, equal_var=False)
            t_stat = float(t_res.statistic)
            p_val = float(t_res.pvalue)

            # Cohen's d
            pooled_std = math.sqrt(((n1 - 1) * (s1**2) + (n2 - 1) * (s2**2)) / (n1 + n2 - 2))
            effect_size = round((m1 - m2) / pooled_std, 3) if pooled_std > 0 else 0.0
            effect_name = "Cohen's d"

            test_type = "Welch's Two-Sample t-test (Parametric)"
            assumptions_note = "Normality assumption satisfied for both groups. Welch's variance correction applied."
        else:
            # Non-parametric Mann-Whitney U
            u_res = stats.mannwhitneyu(g1, g2, alternative="two-sided")
            t_stat = float(u_res.statistic)
            p_val = float(u_res.pvalue)

            # Rank-Biserial correlation r = 1 - (2U / (n1 * n2))
            effect_size = round(1.0 - (2.0 * t_stat / (n1 * n2)), 3)
            effect_name = "Rank-Biserial Correlation (r)"

            test_type = "Mann-Whitney U Test (Non-Parametric)"
            assumptions_note = "Data exhibited non-normal distribution; non-parametric rank test used to ensure validity."

        is_significant = bool(p_val < alpha)

        return {
            "test_type": test_type,
            "group1": {"name": group1_name, "n": n1, "mean": round(m1, 2), "std": round(s1, 2)},
            "group2": {"name": group2_name, "n": n2, "mean": round(m2, 2), "std": round(s2, 2)},
            "statistic": round(t_stat, 4),
            "p_value": round(p_val, 5),
            "alpha": alpha,
            "is_significant": is_significant,
            "effect_size": {"metric": effect_name, "value": effect_size},
            "interpretation": (
                f"Statistically significant difference detected between {group1_name} and {group2_name} (p={round(p_val, 4)} < {alpha})."
                if is_significant
                else f"No statistically significant difference detected between {group1_name} and {group2_name} (p={round(p_val, 4)} >= {alpha})."
            ),
            "assumptions_checked": assumptions_note,
            "causality_caveat": (
                "IMPORTANT: Group differences observed in historical observational data reflect empirical correlation, "
                "not causal effect. Unmeasured confounders or selection bias may account for this difference."
            ),
        }

    @classmethod
    def test_categorical_association(
        cls,
        cat1: pd.Series,
        cat2: pd.Series,
        alpha: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Performs Chi-Square Test of Independence with Cramér's V effect size.
        """
        c1 = cat1.dropna().astype(str)
        c2 = cat2.dropna().astype(str)

        contingency = pd.crosstab(c1, c2)
        if contingency.shape[0] < 2 or contingency.shape[1] < 2:
            return {"error": "Both categorical variables must have at least 2 distinct levels."}

        chi2, p_val, dof, expected = stats.chi2_contingency(contingency)

        # Check Cochran's rule (no expected frequency < 1, and no more than 20% < 5)
        low_expected_pct = (expected < 5).mean() * 100
        sparse_warning = None
        if low_expected_pct > 20:
            sparse_warning = f"Warning: {round(low_expected_pct, 1)}% of cells have expected frequency < 5."

        # Cramér's V
        n = contingency.sum().sum()
        min_dim = min(contingency.shape) - 1
        cramers_v = math.sqrt(chi2 / (n * min_dim)) if n > 0 and min_dim > 0 else 0.0

        is_significant = bool(p_val < alpha)

        return {
            "test_type": "Chi-Square Test of Independence",
            "contingency_shape": list(contingency.shape),
            "total_observations": int(n),
            "chi2_statistic": round(float(chi2), 4),
            "degrees_of_freedom": int(dof),
            "p_value": round(float(p_val), 5),
            "is_significant": is_significant,
            "cramers_v": round(float(cramers_v), 3),
            "sparse_cell_warning": sparse_warning,
            "interpretation": (
                f"Statistically significant association exists between variables (Chi2={round(chi2, 2)}, p={round(p_val, 4)})."
                if is_significant
                else f"No statistically significant association observed (p={round(p_val, 4)} >= {alpha})."
            ),
            "causality_caveat": (
                "NOTE: Statistical association between categorical variables does not imply a causal relationship."
            ),
        }

    @classmethod
    def test_correlation(
        cls,
        series1: pd.Series,
        series2: pd.Series,
        col1_name: str = "Variable 1",
        col2_name: str = "Variable 2",
        alpha: float = 0.05,
    ) -> Dict[str, Any]:
        """
        Evaluates bivariate correlation:
        - Checks normality of both variables.
        - Uses Pearson if bivariate normality holds; otherwise uses Spearman rank correlation.
        - Emphasizes the correlation vs causation distinction.
        """
        df = pd.DataFrame({"x": series1, "y": series2}).dropna()
        if len(df) < 5:
            return {"error": "At least 5 paired observations are required for correlation testing."}

        norm1 = cls.test_normality(df["x"], alpha=alpha)
        norm2 = cls.test_normality(df["y"], alpha=alpha)
        both_normal = norm1.get("is_normal", False) and norm2.get("is_normal", False)

        if both_normal:
            corr_stat, p_val = stats.pearsonr(df["x"], df["y"])
            method = "Pearson Correlation (Linear, Parametric)"
        else:
            corr_stat, p_val = stats.spearmanr(df["x"], df["y"])
            method = "Spearman Rank Correlation (Monotonic, Non-Parametric)"

        abs_corr = abs(corr_stat)
        if abs_corr >= 0.8:
            strength = "very strong"
        elif abs_corr >= 0.5:
            strength = "moderate to strong"
        elif abs_corr >= 0.3:
            strength = "weak to moderate"
        else:
            strength = "negligible"

        direction = "positive" if corr_stat > 0 else "negative"
        is_significant = bool(p_val < alpha)

        return {
            "method": method,
            "variable_1": col1_name,
            "variable_2": col2_name,
            "sample_size": len(df),
            "correlation_coefficient": round(float(corr_stat), 3),
            "p_value": round(float(p_val), 5),
            "is_significant": is_significant,
            "strength": strength,
            "direction": direction,
            "interpretation": (
                f"Statistically significant {direction} {strength} relationship (r={round(corr_stat, 3)}, p={round(p_val, 4)})."
                if is_significant
                else f"No statistically significant correlation observed (r={round(corr_stat, 3)}, p={round(p_val, 4)} >= {alpha})."
            ),
            "causality_caveat": (
                "CRITICAL PRINCIPLE: Correlation does NOT equal causation. A high correlation between "
                f"'{col1_name}' and '{col2_name}' does not prove that one changes the other. "
                "Confounding factors or common underlying drivers often explain statistical associations."
            ),
        }
