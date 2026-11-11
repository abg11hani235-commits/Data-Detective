import time
import os
import sys
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from app.models.schemas import DatasetMetadata
from app.profiler.engine import ProfilingEngine
from app.sandbox.runner import SandboxRunner
from app.config import settings


def generate_benchmark_dataset(num_rows: int = 10_000) -> pd.DataFrame:
    random.seed(42)
    np.random.seed(42)

    categories = ["Electronics", "Office Supplies", "Furniture", "Apparel", "Industrial"]
    regions = ["North", "South", "East", "West", "Central"]
    start_date = datetime(2024, 1, 1)

    dates = [start_date + timedelta(days=random.randint(0, 700)) for _ in range(num_rows)]
    cats = np.random.choice(categories, size=num_rows)
    regs = np.random.choice(regions, size=num_rows)
    quantities = np.random.randint(1, 50, size=num_rows)
    unit_prices = np.round(np.random.uniform(5.0, 500.0, size=num_rows), 2)
    revenues = np.round(quantities * unit_prices, 2)
    costs = np.round(revenues * np.random.uniform(0.4, 0.85, size=num_rows), 2)
    profits = np.round(revenues - costs, 2)

    # Introduce realistic 2% missing values
    rev_with_nan = revenues.astype(float)
    nan_indices = np.random.choice(num_rows, size=int(num_rows * 0.02), replace=False)
    rev_with_nan[nan_indices] = np.nan

    df = pd.DataFrame({
        "order_id": [f"ORD-{100000 + i}" for i in range(num_rows)],
        "order_date": [d.strftime("%Y-%m-%d") for d in dates],
        "category": cats,
        "region": regs,
        "quantity": quantities,
        "unit_price": unit_prices,
        "revenue": rev_with_nan,
        "cost": costs,
        "profit": profits,
    })

    # Add 15 duplicate rows
    df = pd.concat([df, df.iloc[:15]], ignore_index=True)
    return df


async def run_benchmark():
    num_rows = 10_000
    print(f"=== LARGE DATASET BENCHMARK ({num_rows:,} ROWS) ===")

    # 1. Dataset generation
    t0 = time.time()
    df = generate_benchmark_dataset(num_rows)
    gen_time = round((time.time() - t0) * 1000, 2)
    mem_usage_mb = round(df.memory_usage(deep=True).sum() / (1024 * 1024), 2)
    print(f"1. Generation: {len(df):,} rows, {len(df.columns)} cols in {gen_time}ms (Memory: {mem_usage_mb} MB)")

    # 2. Profiling benchmark
    meta = DatasetMetadata(
        id="bench-dataset-10k",
        filename="benchmark_10k.csv",
        file_type="csv",
        row_count=len(df),
        column_count=len(df.columns),
        file_size_bytes=int(df.memory_usage(deep=True).sum()),
        created_at=datetime.utcnow().isoformat() + "Z",
    )

    t0 = time.time()
    profile = ProfilingEngine.profile_dataframe(df, meta)
    profile_time = round((time.time() - t0) * 1000, 2)
    print(f"2. Profiling Time: {profile_time}ms")
    print(f"   Quality Score: {profile.data_quality_score}/100")
    print(f"   Missing Cells: {profile.total_missing_cells:,} ({profile.missing_cells_percentage}%)")
    print(f"   Duplicates: {profile.duplicate_rows}")

    # 3. Sandbox execution benchmark
    temp_csv = settings.DATA_DIR / "benchmark_10k.csv"
    df.to_csv(temp_csv, index=False)

    analysis_code = """
import json
import pandas as pd
import numpy as np
import plotly.express as px

# High-throughput aggregation on 10k rows
agg = df.groupby('category').agg(
    total_rev=('revenue', 'sum'),
    avg_profit=('profit', 'mean'),
    order_count=('quantity', 'count')
).reset_index()

top_cat = agg.sort_values(by='total_rev', ascending=False).iloc[0]

fig = px.bar(agg, x='category', y='total_rev', title="Revenue by Category", template="plotly_dark")

output_data = {
    "status": "success",
    "tables": [{
        "name": "category_performance",
        "columns": list(agg.columns),
        "data": agg.round(2).to_dict(orient="records")
    }],
    "metrics": {
        "top_category": str(top_cat['category']),
        "total_dataset_revenue": round(float(df['revenue'].sum()), 2),
        "avg_profit_margin_pct": round(float((df['profit'].sum() / df['revenue'].sum()) * 100), 2)
    },
    "charts": [{
        "figure": json.loads(fig.to_json()),
        "caption": "Category revenue breakdown"
    }],
    "warnings": []
}

with open("output/results.json", "w") as f:
    json.dump(output_data, f, default=str)
"""

    t0 = time.time()
    exec_output = await SandboxRunner.execute(
        code=analysis_code,
        dataset_path=temp_csv,
        file_type="csv",
        timeout_seconds=15,
    )
    sandbox_time = round((time.time() - t0) * 1000, 2)

    assert exec_output.status == "success"
    assert "top_category" in exec_output.metrics
    assert len(exec_output.charts) == 1

    print(f"3. Sandbox Subprocess Execution Time: {sandbox_time}ms")
    print(f"   Computed Total Revenue: ${exec_output.metrics['total_dataset_revenue']:,.2f}")
    print(f"   Top Category: {exec_output.metrics['top_category']}")
    print(f"   Avg Profit Margin: {exec_output.metrics['avg_profit_margin_pct']}%")

    # Clean up benchmark file
    try:
        temp_csv.unlink(missing_ok=True)
    except Exception:
        pass

    print("\nBENCHMARK COMPLETED SUCCESSFULLY!")


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_benchmark())
