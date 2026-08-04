"""Unit tests for the analytics provider abstraction."""
from app.analytics.provider import MockAnalyticsProvider


def test_mock_compliance_refresh_succeeds():
    p = MockAnalyticsProvider()
    job_id = p.submit_compliance_refresh("exp_1")
    assert p.get_job_status(job_id).status == "SUCCEEDED"


def test_mock_simulation_returns_result():
    p = MockAnalyticsProvider()
    p.submit_policy_simulation({"simulation_id": "sim_1", "policy_definition": {}})
    result = p.get_simulation_result("sim_1")
    assert result["simulation_id"] == "sim_1"
    assert result["requests_affected"] > 0
    assert "risk_distribution" in result


def test_unknown_job_status_is_failed():
    p = MockAnalyticsProvider()
    assert p.get_job_status("nope").status == "FAILED"
