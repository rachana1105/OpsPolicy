"""Unit tests for risk scoring and state-transition validation."""
import pytest

from app.core.errors import InvalidStateTransitionError
from app.models.enums import RequestStatus as R
from app.risk_engine import RiskEngine, level_for_score
from app.workflow.transitions import assert_transition


def test_risk_levels():
    assert level_for_score(0) == "LOW"
    assert level_for_score(5) == "LOW"
    assert level_for_score(6) == "MEDIUM"
    assert level_for_score(12) == "HIGH"
    assert level_for_score(20) == "CRITICAL"


def test_restricted_export_contractor_is_critical():
    context = {
        "request": {"requested_action": "EXPORT", "destination_region": "US", "duration_days": 30},
        "resource": {"sensitivity": "RESTRICTED", "criticality": "CRITICAL"},
        "requester": {"employee_type": "CONTRACTOR"},
    }
    result = RiskEngine().score(context, history={"previous_exceptions": 1})
    names = {f.name for f in result.factors}
    assert "restricted_resource" in names
    assert "export_action" in names
    assert "external_export" in names
    assert "long_duration" in names
    assert "contractor" in names
    assert "previous_exception" in names
    assert result.risk_level == "CRITICAL"


def test_purchase_amount_bands():
    r1 = RiskEngine().score({"request": {"amount": 600000}, "resource": {}, "requester": {}})
    assert any(f.name == "high_purchase_amount" for f in r1.factors)
    r2 = RiskEngine().score({"request": {"amount": 1200000}, "resource": {}, "requester": {}})
    assert any(f.name == "very_high_purchase_amount" for f in r2.factors)


def test_valid_transition():
    assert_transition(R.DRAFT, R.SUBMITTED)  # no raise
    assert_transition(R.ACTIVE, R.EXPIRING)


def test_invalid_transition_raises():
    with pytest.raises(InvalidStateTransitionError) as exc:
        assert_transition(R.APPROVED, R.UNDER_REVIEW)
    assert exc.value.details["current_state"] == "APPROVED"
