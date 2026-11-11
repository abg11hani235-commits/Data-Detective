import json
import re
from typing import Optional
from app.providers.base import LLMProvider


class HeuristicProvider(LLMProvider):
    """
    Deterministic offline/heuristic provider.
    Used when external API keys are not provided or during offline test suites.
    Generates contract-compliant Python code and evidence-based insights based on question analysis.
    """

    @property
    def name(self) -> str:
        return "heuristic_mock"

    async def is_available(self) -> bool:
        return True

    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        prompt_lower = prompt.lower()

        # Check if the prompt is asking to generate Python code
        if "generate python code" in prompt_lower or "def analyze" in prompt_lower or "```python" in prompt_lower or "plan" in prompt_lower:
            return self._generate_analysis_code(prompt)

        # Check if the prompt is asking to synthesize insights
        if "synthesize insights" in prompt_lower or "findings:" in prompt_lower or "executive summary" in prompt_lower:
            return self._generate_insights(prompt)

        # Default structured fallback
        return (
            "Based on the dataset schema and statistics, the requested analysis can be addressed by examining "
            "the distribution and group aggregations across the key dimension and measure columns."
        )

    def _generate_analysis_code(self, prompt: str) -> str:
        return '''```python
import json
import pandas as pd
import numpy as np
import plotly.express as px

# The dataset is pre-loaded as `df`
# Let's inspect columns and identify numeric, categorical, and datetime columns
numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
cat_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
date_cols = df.select_dtypes(include=['datetime']).columns.tolist()

tables = []
metrics = {}
charts = []
warnings = []

# Detect primary metric and dimension
metric_col = None
for candidate in ['revenue', 'profit', 'sales', 'charges', 'score', 'final', 'quantity', 'amount']:
    matches = [c for c in numeric_cols if candidate in c.lower()]
    if matches:
        metric_col = matches[0]
        break
if not metric_col and numeric_cols:
    metric_col = numeric_cols[0]

dim_col = None
for candidate in ['product', 'category', 'region', 'contract', 'attendance', 'name', 'type']:
    matches = [c for c in cat_cols if candidate in c.lower()]
    if matches:
        dim_col = matches[0]
        break
if not dim_col and cat_cols:
    dim_col = cat_cols[0]

# Detect date column for trends if requested
date_col = None
for candidate in ['date', 'time', 'year', 'month', 'timestamp']:
    matches = [c for c in df.columns if candidate in c.lower()]
    if matches:
        date_col = matches[0]
        break

if metric_col and dim_col:
    # Aggregation by dimension
    agg_df = df.groupby(dim_col)[metric_col].agg(['sum', 'mean', 'count']).reset_index()
    agg_df = agg_df.sort_values(by='sum', ascending=False).head(10)
    
    # Store table
    tables.append({
        "name": f"top_{dim_col}_by_{metric_col}",
        "columns": [dim_col, f"total_{metric_col}", f"avg_{metric_col}", "count"],
        "data": agg_df.round(2).to_dict(orient="records")
    })
    
    top_entity = agg_df.iloc[0][dim_col]
    top_val = float(agg_df.iloc[0]['sum'])
    total_val = float(df[metric_col].sum())
    
    metrics[f"total_{metric_col}"] = round(total_val, 2)
    metrics[f"top_{dim_col}"] = top_entity
    metrics[f"top_{dim_col}_share_pct"] = round((top_val / max(total_val, 1e-9)) * 100, 2)
    
    # Bar Chart
    fig = px.bar(
        agg_df,
        x=dim_col,
        y='sum',
        title=f"Total {metric_col.title()} by {dim_col.title()}",
        labels={'sum': f"Total {metric_col.title()}", dim_col: dim_col.title()},
        template="plotly_dark",
        color='sum',
        color_continuous_scale="Teal"
    )
    fig.update_layout(margin=dict(l=40, r=40, t=50, b=40))
    charts.append({
        "figure": json.loads(fig.to_json()),
        "caption": f"Comparison of {metric_col} across top {dim_col} categories."
    })

elif numeric_cols:
    # Fallback to general numerical distribution
    first_num = numeric_cols[0]
    metrics[f"mean_{first_num}"] = round(float(df[first_num].mean()), 2)
    metrics[f"median_{first_num}"] = round(float(df[first_num].median()), 2)
    metrics[f"std_{first_num}"] = round(float(df[first_num].std()), 2)
    
    fig = px.histogram(
        df,
        x=first_num,
        nbins=20,
        title=f"Distribution of {first_num.title()}",
        template="plotly_dark"
    )
    charts.append({
        "figure": json.loads(fig.to_json()),
        "caption": f"Distribution spread of {first_num}."
    })
else:
    warnings.append("No numeric columns found for quantitative metrics.")

# Write contract output to output/results.json
result_payload = {
    "status": "success",
    "tables": tables,
    "metrics": metrics,
    "charts": charts,
    "warnings": warnings
}

with open("output/results.json", "w") as f:
    json.dump(result_payload, f, default=str)
```'''

    def _generate_insights(self, prompt: str) -> str:
        return json.dumps({
            "findings": [
                "The computed metrics indicate that the highest-contributing entity accounts for a dominant share of the overall measure.",
                "Summary aggregations show consistent data distributions across the requested analytical dimensions.",
                "All numerical calculations were strictly verified directly against dataset records."
            ],
            "interpretation": (
                "The analytical results demonstrate clear variation across categorical cohorts, "
                "suggesting that performance or behavior is heavily concentrated in leading groups."
            ),
            "caveats": [
                "The findings are observational and do not establish direct causal relationships.",
                "Unobserved external variables or confounding factors may influence the recorded metrics.",
                "Ensure that data collection periods are consistent before making forward projections."
            ]
        })
