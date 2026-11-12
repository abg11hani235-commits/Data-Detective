from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalyticalStep(BaseModel):
    step_id: int
    title: str
    action: str  # "prepare_data", "aggregate_metrics", "statistical_test", "visualize", "synthesize"
    description: str
    target_columns: List[str] = Field(default_factory=list)
    expected_output: str


class StructuredAnalyticalPlan(BaseModel):
    question: str
    complexity: str  # "simple", "moderate", "complex_multi_step"
    intent: str  # "descriptive", "group_comparison", "correlation", "trend", "outlier_analysis"
    steps: List[AnalyticalStep]
    requires_statistical_testing: bool = False
    suggested_visualizations: List[str] = Field(default_factory=list)

    def to_formatted_markdown(self) -> str:
        lines = [
            f"### Analytical Plan ({self.complexity.replace('_', ' ').title()})",
            f"**Intent:** {self.intent.replace('_', ' ').title()} | **Statistical Testing:** {'Required' if self.requires_statistical_testing else 'Not Required'}",
            "",
            "#### Execution Steps:",
        ]
        for step in self.steps:
            cols = f" (Columns: {', '.join(step.target_columns)})" if step.target_columns else ""
            lines.append(f"{step.step_id}. **{step.title}** [{step.action}]{cols}: {step.description} -> *Output:* {step.expected_output}")
        return "\n".join(lines)


class AnalyticalPlanner:
    """
    Intelligent query decomposition engine.
    Transforms arbitrary natural-language analytical questions into
    deterministic, step-by-step execution plans.
    """

    COMPARISON_KEYWORDS = ["compare", "difference", "vs", "versus", "higher than", "lower than", "better", "worse"]
    CORRELATION_KEYWORDS = ["correlation", "relationship", "correlated", "relate", "association", "impact", "affect"]
    TREND_KEYWORDS = ["trend", "over time", "monthly", "yearly", "growth", "trajectory", "historical"]
    OUTLIER_KEYWORDS = ["outlier", "anomaly", "abnormal", "extreme", "unusual"]
    STATISTICAL_KEYWORDS = ["significant", "statistically", "hypothesis", "p-value", "confidence"]

    @classmethod
    def create_plan(
        cls,
        question: str,
        column_profiles: List[Dict[str, Any]],
        row_count: int = 0,
    ) -> StructuredAnalyticalPlan:
        q_lower = question.lower()
        col_names = [c.get("name", "") for c in column_profiles]

        # Identify referenced columns
        referenced_cols = [c for c in col_names if c.lower() in q_lower]

        # Detect intent
        is_stat = any(k in q_lower for k in cls.STATISTICAL_KEYWORDS)
        is_comp = any(k in q_lower for k in cls.COMPARISON_KEYWORDS)
        is_corr = any(k in q_lower for k in cls.CORRELATION_KEYWORDS)
        is_trend = any(k in q_lower for k in cls.TREND_KEYWORDS)
        is_outlier = any(k in q_lower for k in cls.OUTLIER_KEYWORDS)

        steps: List[AnalyticalStep] = []
        intent = "descriptive"
        requires_stat = is_stat
        complexity = "simple"
        suggested_charts = []

        if is_comp:
            intent = "group_comparison"
            complexity = "moderate" if not is_stat else "complex_multi_step"
            suggested_charts.append("grouped_bar_or_box_plot")
            steps = [
                AnalyticalStep(
                    step_id=1,
                    title="Data Validation & Group Partitioning",
                    action="prepare_data",
                    description="Filter nulls in grouping and metric columns, group observations by categorical factor.",
                    target_columns=referenced_cols,
                    expected_output="Clean partitioned group subsets",
                ),
                AnalyticalStep(
                    step_id=2,
                    title="Compute Comparative Group Statistics",
                    action="aggregate_metrics",
                    description="Calculate group sample size (N), mean, median, standard deviation, and relative difference.",
                    target_columns=referenced_cols,
                    expected_output="Group comparison summary table",
                ),
                AnalyticalStep(
                    step_id=3,
                    title="Statistical Significance & Effect Size",
                    action="statistical_test",
                    description="Verify distribution assumptions and run Welch's t-test or Mann-Whitney U test with effect size.",
                    target_columns=referenced_cols,
                    expected_output="P-value, test statistic, and standardized effect size",
                ),
                AnalyticalStep(
                    step_id=4,
                    title="Interactive Comparative Visualization",
                    action="visualize",
                    description="Generate Plotly box plot or grouped bar chart displaying distributions and error bars.",
                    target_columns=referenced_cols,
                    expected_output="Plotly figure spec",
                ),
            ]
            requires_stat = True

        elif is_corr:
            intent = "correlation"
            complexity = "moderate"
            suggested_charts.append("scatter_plot_with_trendline")
            steps = [
                AnalyticalStep(
                    step_id=1,
                    title="Pairwise Numeric Alignment",
                    action="prepare_data",
                    description="Extract paired numeric variables and drop any rows containing incomplete pairs.",
                    target_columns=referenced_cols,
                    expected_output="Paired observation vectors",
                ),
                AnalyticalStep(
                    step_id=2,
                    title="Calculate Correlation & Covariance",
                    action="aggregate_metrics",
                    description="Compute Pearson linear coefficient and Spearman rank coefficient.",
                    target_columns=referenced_cols,
                    expected_output="Correlation coefficients and covariance matrix",
                ),
                AnalyticalStep(
                    step_id=3,
                    title="Bivariate Scatter & Trendline Plotting",
                    action="visualize",
                    description="Render Plotly scatter plot with OLS trendline showing the relationship.",
                    target_columns=referenced_cols,
                    expected_output="Plotly scatter spec",
                ),
            ]

        elif is_trend:
            intent = "trend"
            complexity = "moderate"
            suggested_charts.append("time_series_line_chart")
            steps = [
                AnalyticalStep(
                    step_id=1,
                    title="Datetime Parsing & Chronological Sorting",
                    action="prepare_data",
                    description="Convert date column to datetime index and sort records chronologically.",
                    target_columns=referenced_cols,
                    expected_output="Time-indexed DataFrame",
                ),
                AnalyticalStep(
                    step_id=2,
                    title="Temporal Resampling & Aggregation",
                    action="aggregate_metrics",
                    description="Resample by desired frequency (monthly/quarterly) and calculate sum/average.",
                    target_columns=referenced_cols,
                    expected_output="Aggregated time-series table",
                ),
                AnalyticalStep(
                    step_id=3,
                    title="Time Series Line Visualization",
                    action="visualize",
                    description="Build interactive Plotly line chart with rolling averages.",
                    target_columns=referenced_cols,
                    expected_output="Plotly line chart spec",
                ),
            ]

        elif is_outlier:
            intent = "outlier_analysis"
            complexity = "moderate"
            suggested_charts.append("box_plot_or_histogram")
            steps = [
                AnalyticalStep(
                    step_id=1,
                    title="Outlier Boundary Computation",
                    action="prepare_data",
                    description="Compute Q1, Q3, IQR, and Z-scores for target metric.",
                    target_columns=referenced_cols,
                    expected_output="Upper and lower outlier bounds",
                ),
                AnalyticalStep(
                    step_id=2,
                    title="Isolate Anomalous Observations",
                    action="aggregate_metrics",
                    description="Filter rows beyond 1.5*IQR and compute outlier frequency and percentage.",
                    target_columns=referenced_cols,
                    expected_output="Table of detected outlier records",
                ),
                AnalyticalStep(
                    step_id=3,
                    title="Outlier Highlighting Visualization",
                    action="visualize",
                    description="Generate distribution box plot highlighting anomalous points in distinct color.",
                    target_columns=referenced_cols,
                    expected_output="Plotly box plot spec",
                ),
            ]

        else:
            intent = "descriptive"
            complexity = "simple"
            suggested_charts.append("bar_chart")
            steps = [
                AnalyticalStep(
                    step_id=1,
                    title="Data Filtering & Extraction",
                    action="prepare_data",
                    description="Select target columns and remove missing values.",
                    target_columns=referenced_cols,
                    expected_output="Clean DataFrame subset",
                ),
                AnalyticalStep(
                    step_id=2,
                    title="Metric Calculation",
                    action="aggregate_metrics",
                    description="Compute targeted descriptive statistics (sum, mean, median, min, max, count).",
                    target_columns=referenced_cols,
                    expected_output="Dictionary of computed metrics",
                ),
                AnalyticalStep(
                    step_id=3,
                    title="Summary Visualization",
                    action="visualize",
                    description="Render informative Plotly summary chart.",
                    target_columns=referenced_cols,
                    expected_output="Plotly chart spec",
                ),
            ]

        return StructuredAnalyticalPlan(
            question=question,
            complexity=complexity,
            intent=intent,
            steps=steps,
            requires_statistical_testing=requires_stat,
            suggested_visualizations=suggested_charts,
        )
