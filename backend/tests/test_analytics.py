"""Tests for export, compliance metrics, and historical simulation (M7)."""
import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("EXPORT_ROOT", "/tmp/opspolicy_test_exports")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base, utcnow  # noqa: E402
import app.models  # noqa: E402,F401
from app.core.security import hash_password  # noqa: E402
from app.models.enums import (  # noqa: E402
    Criticality, EmployeeType, RequestStatus, RequestType, ResourceType, Role,
    RiskLevel, Sensitivity, Decision,
)
from app.models.org import Organisation, Resource, User  # noqa: E402
from app.models.request import Request  # noqa: E402
from app.services.analytics_service import AnalyticsService  # noqa: E402
from app.analytics.export_service import ExportService  # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    s = Session()
    org = Organisation(name="Org"); s.add(org); s.flush()
    emp = User(organisation_id=org.id, name="Emp", email="e@t.io", role=Role.EMPLOYEE,
               employee_type=EmployeeType.EMPLOYEE, password_hash=hash_password("pw"))
    contractor = User(organisation_id=org.id, name="Con", email="c@t.io", role=Role.EMPLOYEE,
                      employee_type=EmployeeType.CONTRACTOR, password_hash=hash_password("pw"))
    s.add_all([emp, contractor]); s.flush()
    res = Resource(organisation_id=org.id, name="prod-svc", resource_type=ResourceType.PRODUCTION_SERVICE,
                   criticality=Criticality.HIGH, sensitivity=Sensitivity.CONFIDENTIAL, region="IN")
    s.add(res); s.flush()

    # Seed historical requests in various states.
    def mk(requester, status, risk, payload, days_ago_created=1):
        r = Request(organisation_id=org.id, request_type=RequestType.PRODUCTION_ACCESS,
                    requester_id=requester.id, resource_id=res.id, title="t",
                    request_payload=payload, status=status, risk_level=risk, risk_score=10,
                    submitted_at=utcnow(), approved_at=utcnow() if status == RequestStatus.APPROVED else None)
        s.add(r); s.flush(); return r

    # Contractor prod-access requests, some approved with long durations.
    mk(contractor, RequestStatus.APPROVED, RiskLevel.HIGH, {"requested_role": "READ", "duration_days": 30})
    mk(contractor, RequestStatus.APPROVED, RiskLevel.MEDIUM, {"requested_role": "READ", "duration_days": 14})
    mk(emp, RequestStatus.APPROVED, RiskLevel.LOW, {"requested_role": "READ", "duration_days": 3})
    mk(emp, RequestStatus.REJECTED, RiskLevel.HIGH, {"requested_role": "ADMIN", "duration_days": 5})
    s.commit()
    s.org_id = org.id; s.contractor_id = contractor.id
    yield s
    s.close()


def test_compliance_refresh_produces_summary(db):
    svc = AnalyticsService(db)
    job = svc.refresh_compliance(db.org_id); db.commit()
    assert job.status.value == "SUCCEEDED"
    summary = job.result_payload["compliance_summary"]
    assert summary["total_requests"] == 4
    assert summary["approved"] == 3
    assert summary["rejected"] == 1
    assert "risk_distribution" in summary


def test_export_writes_manifest_and_files(db):
    svc = ExportService(db)
    manifest = svc.run_export(db.org_id); db.commit()
    assert "export_id" in manifest
    assert manifest["tables"]["requests"]["row_count"] == 4
    # manifest file exists
    export_dir = os.path.join("/tmp/opspolicy_test_exports", manifest["export_id"])
    assert os.path.exists(os.path.join(export_dir, "manifest.json"))
    assert os.path.exists(os.path.join(export_dir, "requests.ndjson"))


def test_simulation_contractor_7day_cap(db):
    """Proposed: contractor prod access capped at 7 days. Should flag the two
    contractor requests with 30- and 14-day durations as affected/duration-reduced."""
    proposed = {
        "name": "Contractor prod access max 7 days",
        "applies_to": {"request_type": "PRODUCTION_ACCESS"},
        "conditions": {"all": [
            {"field": "requester.employee_type", "operator": "EQUALS", "value": "CONTRACTOR"}]},
        "actions": [{"type": "SET_MAXIMUM_DURATION", "days": 7}],
    }
    svc = AnalyticsService(db)
    job = svc.create_simulation(db.org_id, policy_definition=proposed); db.commit()
    result = job.result_payload
    assert result["records_analysed"] == 4
    # two contractor requests exceed 7 days
    assert result["duration_reductions_required"] == 2
    assert result["requests_affected"] == 2
    assert result["recommendation"] in (
        "SAFE_TO_INTRODUCE", "INTRODUCE_GRADUALLY", "HIGH_IMPACT_REVIEW_BEFORE_ROLLOUT")


def test_simulation_reject_policy_flags_previously_approved(db):
    """Proposed: reject all contractor prod access. Two previously-approved
    contractor requests should count as previously_approved_now_rejected."""
    proposed = {
        "name": "No contractor prod access",
        "applies_to": {"request_type": "PRODUCTION_ACCESS"},
        "conditions": {"all": [
            {"field": "requester.employee_type", "operator": "EQUALS", "value": "CONTRACTOR"}]},
        "actions": [{"type": "REJECT", "reason": "Contractors may not access production"}],
    }
    svc = AnalyticsService(db)
    job = svc.create_simulation(db.org_id, policy_definition=proposed); db.commit()
    result = job.result_payload
    assert result["previously_approved_now_rejected"] == 2


def test_analytics_unavailable_before_refresh(db):
    """Compliance summary reports unavailable until a refresh has run."""
    svc = AnalyticsService(db)
    assert svc.latest_compliance(db.org_id) is None
