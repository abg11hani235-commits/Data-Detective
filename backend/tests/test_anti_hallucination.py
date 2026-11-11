import pytest
from app.agent.verifier import FindingsValidator


def test_grounded_findings_pass():
    metrics = {"total_revenue": 142500.5, "growth_rate": 18.4}
    tables = [{"data": [{"product": "Laptop", "revenue": 142500.5}]}]
    metadata = {"row_count": 250, "column_count": 9}

    findings = [
        "Total revenue reached $142,500.50 across the dataset.",
        "A growth rate of 18.4% was recorded.",
    ]

    approved, caveats = FindingsValidator.verify_findings(findings, metrics, tables, metadata)
    assert len(approved) == 2
    assert len(caveats) == 0


def test_fabricated_numbers_are_rejected_and_flagged():
    """
    Test where the LLM output contains a fabricated number (e.g. $999,999 or 88.5%)
    that does not exist in execution metrics or tables.
    The fabricated claim MUST NOT be presented as an approved finding.
    """
    metrics = {"total_revenue": 50000.0, "average_order": 120.0}
    tables = [{"data": [{"region": "North", "sales": 30000.0}]}]
    metadata = {"row_count": 100, "column_count": 5}

    findings = [
        "Total revenue calculated directly from records was 50000.0.",
        "Revenue mysteriously reached $999,999.00 according to an imaginary report.",  # FABRICATED NUMBER
        "Churn skyrocketed to 88.5% in the region.",  # FABRICATED NUMBER
    ]

    approved, caveats = FindingsValidator.verify_findings(findings, metrics, tables, metadata)

    # The 2 fabricated findings MUST be stripped from approved findings!
    assert len(approved) == 1
    assert "50000.0" in approved[0]

    # The caveats must document the rejection of the fabricated claims
    assert len(caveats) == 2
    assert any("999999" in c for c in caveats)
    assert any("88.5" in c for c in caveats)
