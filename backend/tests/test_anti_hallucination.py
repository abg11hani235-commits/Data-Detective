import pytest
from app.agent.verifier import EvidenceRegistry, FindingsValidator
from app.models.schemas import Claim


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
    metrics = {"total_revenue": 50000.0, "average_order": 120.0}
    tables = [{"data": [{"region": "North", "sales": 30000.0}]}]
    metadata = {"row_count": 100, "column_count": 5}

    findings = [
        "Total revenue calculated directly from records was 50000.0.",
        "Revenue mysteriously reached $999,999.00 according to an imaginary report.",  # FABRICATED
        "Churn skyrocketed to 88.5% in the region.",  # FABRICATED
    ]

    approved, caveats = FindingsValidator.verify_findings(findings, metrics, tables, metadata)
    assert len(approved) == 1
    assert "50000.0" in approved[0]
    assert len(caveats) == 2
    assert any("999999" in c for c in caveats)
    assert any("88.5" in c for c in caveats)


def test_claim_structured_correct_verification():
    registry = EvidenceRegistry()
    registry.register(source="metrics", metric_name="churn_rate", value=14.2)
    registry.register(source="table:regional", metric_name="sales", entity="North", value=45000.0)

    claim = Claim(
        id="c1",
        statement="North region achieved $45,000 in sales.",
        metric_name="sales",
        entity="North",
        claimed_value=45000.0,
    )

    validated = FindingsValidator.validate_claim(claim, registry)
    assert validated.validation_status == "verified"
    assert validated.evidence_id is not None
    assert "Verified against" in validated.reason


def test_claim_incorrect_numerical_value():
    registry = EvidenceRegistry()
    registry.register(source="metrics", metric_name="operating_margin", value=22.5)

    claim = Claim(
        id="c2",
        statement="Operating margin reached 35.0%.",
        metric_name="operating_margin",
        claimed_value=35.0,  # Incorrect number
    )

    validated = FindingsValidator.validate_claim(claim, registry)
    assert validated.validation_status == "unsupported"
    assert "Claim asserted 35.0" in validated.reason
    assert "verified computed value is 22.5" in validated.reason


def test_claim_correct_number_wrong_context():
    """
    Number 85.0 exists in evidence, but it belongs to 'customer_satisfaction',
    NOT 'churn_rate'. The validator must flag this context mismatch!
    """
    registry = EvidenceRegistry()
    registry.register(source="metrics", metric_name="customer_satisfaction", value=85.0)
    registry.register(source="metrics", metric_name="churn_rate", value=12.0)

    claim = Claim(
        id="c3",
        statement="The churn rate was 85%.",
        metric_name="churn_rate",
        claimed_value=85.0,
    )

    validated = FindingsValidator.validate_claim(claim, registry)
    assert validated.validation_status == "context_mismatch"
    assert "Context mismatch" in validated.reason
    assert "customer_satisfaction" in validated.reason


def test_claim_missing_evidence():
    """Claim asserts a metric that was never computed anywhere in execution."""
    registry = EvidenceRegistry()
    registry.register(source="metrics", metric_name="revenue", value=100000.0)

    claim = Claim(
        id="c4",
        statement="Customer lifetime value is $1,200.",
        metric_name="clv",
        claimed_value=1200.0,
    )

    validated = FindingsValidator.validate_claim(claim, registry)
    assert validated.validation_status == "missing_evidence"
    assert "No computed result found for metric 'clv'" in validated.reason


def test_claim_entity_swap_context_mismatch():
    """
    North had 500 sales, South had 200 sales.
    Claim asserts North had 200 sales.
    """
    registry = EvidenceRegistry()
    registry.register(source="table:regional", metric_name="sales", entity="North", value=500.0)
    registry.register(source="table:regional", metric_name="sales", entity="South", value=200.0)

    claim = Claim(
        id="c5",
        statement="North region had 200 sales.",
        metric_name="sales",
        entity="North",
        claimed_value=200.0,
    )

    validated = FindingsValidator.validate_claim(claim, registry)
    # The value 200.0 belongs to entity South, while North actually has 500
    assert validated.validation_status in ["unsupported", "context_mismatch"]
