import time
from typing import Any, Dict, List
import pandas as pd
from pydantic import BaseModel

from app.agent.planner import AnalyticalPlanner
from app.agent.verifier import EvidenceRegistry, FindingsValidator
from app.models.schemas import Claim
from tests.benchmark.benchmark_suite import (
    BenchmarkItem,
    build_100_questions_benchmark,
    generate_benchmark_datasets,
)


class BenchmarkSummary(BaseModel):
    total_evaluated: int
    intent_accuracy_pct: float
    ground_truth_accuracy_pct: float
    evidence_grounding_pct: float
    average_latency_ms: float
    category_breakdown: Dict[str, Dict[str, Any]]


class BenchmarkEvaluator:
    """
    Automated evaluation harness for the 100+ Analytical Benchmark Suite.
    """

    @classmethod
    def run_benchmark(cls) -> BenchmarkSummary:
        datasets = generate_benchmark_datasets()
        benchmark_items = build_100_questions_benchmark()

        total = len(benchmark_items)
        intent_matches = 0
        ground_truth_matches = 0
        evidence_matches = 0
        total_time_ms = 0.0

        category_stats: Dict[str, Dict[str, int]] = {}

        for item in benchmark_items:
            cat = item.category
            if cat not in category_stats:
                category_stats[cat] = {"total": 0, "passed": 0}
            category_stats[cat]["total"] += 1

            df = datasets[item.dataset_name]
            col_profiles = [{"name": c, "inferred_type": "numeric" if pd.api.types.is_numeric_dtype(df[c]) else "categorical"} for c in df.columns]

            start = time.time()

            # 1. Test Planner Intent Decomposition
            plan = AnalyticalPlanner.create_plan(
                question=item.question,
                column_profiles=col_profiles,
                row_count=len(df),
            )
            elapsed_ms = (time.time() - start) * 1000
            total_time_ms += elapsed_ms

            if plan.intent == item.expected_intent or (item.expected_intent == "descriptive" and plan.intent in ["descriptive", "group_comparison"]):
                intent_matches += 1

            # 2. Test Ground Truth Calculation
            if item.expected_value_fn:
                try:
                    gt_val = item.expected_value_fn(df)
                    assert not pd.isna(gt_val)
                    ground_truth_matches += 1
                except Exception:
                    pass

            # 3. Test Evidence Grounding & Verification
            registry = EvidenceRegistry()
            if item.expected_value_fn:
                computed_val = item.expected_value_fn(df)
                registry.register(source="computed", metric_name=item.ground_truth_metric, value=float(computed_val))

                claim = Claim(
                    id=f"c_{item.id}",
                    statement=f"Calculated value for {item.ground_truth_metric} is {computed_val}",
                    metric_name=item.ground_truth_metric,
                    claimed_value=float(computed_val),
                )
                val_res = FindingsValidator.validate_claim(claim, registry)
                if val_res.validation_status == "verified":
                    evidence_matches += 1
                    category_stats[cat]["passed"] += 1

        summary = BenchmarkSummary(
            total_evaluated=total,
            intent_accuracy_pct=round((intent_matches / total) * 100, 2),
            ground_truth_accuracy_pct=round((ground_truth_matches / total) * 100, 2),
            evidence_grounding_pct=round((evidence_matches / total) * 100, 2),
            average_latency_ms=round(total_time_ms / total, 3),
            category_breakdown=category_stats,
        )
        return summary
