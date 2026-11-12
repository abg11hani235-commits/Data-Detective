import pytest
from tests.benchmark.evaluator import BenchmarkEvaluator


def test_100_question_evaluation_benchmark():
    """
    Executes the 100+ Question Analytical Ground-Truth Benchmark.
    Verifies that:
    - At least 100 benchmark items are evaluated (we have 105)
    - Intent decomposition accuracy exceeds 90%
    - Ground-truth mathematical reproducibility is 100%
    - Evidence grounding verification rate is 100%
    """
    summary = BenchmarkEvaluator.run_benchmark()

    assert summary.total_evaluated >= 100, f"Expected >= 100 benchmark items, got {summary.total_evaluated}"
    assert summary.ground_truth_accuracy_pct == 100.0, f"Ground-truth calculation accuracy was {summary.ground_truth_accuracy_pct}%"
    assert summary.evidence_grounding_pct == 100.0, f"Evidence grounding verification rate was {summary.evidence_grounding_pct}%"
    assert summary.intent_accuracy_pct >= 90.0, f"Planner intent accuracy was {summary.intent_accuracy_pct}%"

    print("\n" + "=" * 60)
    print(f"BENCHMARK RESULTS (Total: {summary.total_evaluated} questions evaluated)")
    print(f"Intent Decomposition Accuracy: {summary.intent_accuracy_pct}%")
    print(f"Ground-Truth Accuracy:         {summary.ground_truth_accuracy_pct}%")
    print(f"Evidence Grounding Rate:       {summary.evidence_grounding_pct}%")
    print(f"Average Planning Latency:      {summary.average_latency_ms} ms/query")
    print("=" * 60)
    for cat, stats in summary.category_breakdown.items():
        print(f"  - {cat:28s}: {stats['passed']}/{stats['total']} passed")
    print("=" * 60)
