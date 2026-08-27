import pytest
from pydantic import ValidationError

from src.models.account_health import RiskFlag
from src.models.triage import Classification


def test_classification_rejects_bad_urgency_enum():
    with pytest.raises(ValidationError):
        Classification(
            product="DataBridge Pro",
            product_area="Connectors",
            category="Bug",
            urgency="P9",  # invalid
            reasoning="test",
        )


def test_classification_unknown_product_is_flagged_not_rejected():
    c = Classification(
        product="SomeRandomProduct",
        product_area="Connectors",
        category="Bug",
        urgency="P3",
        reasoning="test",
    )
    assert c.product == "Unknown"


def test_risk_flag_requires_severity_enum():
    with pytest.raises(ValidationError):
        RiskFlag(
            risk_type="x",
            severity="Super Critical",  # invalid
            explanation="x",
            supporting_ticket_id="T1",
            quote="x",
        )
