"""Integration tests for the request lifecycle (Milestone 3).

Uses an in-memory SQLite database seeded with a minimal org so the full submit
flow — evaluate, score, persist evaluations, generate workflow, audit — runs
end to end through the API.
"""
import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base  # noqa: E402
import app.models  # noqa: E402,F401
from app.core.security import hash_password  # noqa: E402
from app.db.seed_policies import SEED_POLICIES  # noqa: E402
from app.models.enums import (  # noqa: E402
    Criticality, EmployeeType, PolicyStatus, PolicyType, ResourceType, Role, Sensitivity,
)
from app.models.org import Organisation, Resource, User  # noqa: E402
from app.models.policy import Policy, PolicyVersion  # noqa: E402


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    db = TestingSession()
    org = Organisation(name="TestOrg")
    db.add(org); db.flush()

    def mk(name, email, role, emp=EmployeeType.EMPLOYEE, manager=None):
        u = User(organisation_id=org.id, name=name, email=email, role=role,
                 employee_type=emp, manager_id=manager.id if manager else None,
                 password_hash=hash_password("pw"))
        db.add(u); db.flush(); return u

    mgr = mk("Mgr", "mgr@t.io", Role.MANAGER)
    owner = mk("Owner", "owner@t.io", Role.DATA_OWNER)
    comp = mk("Comp", "comp@t.io", Role.COMPLIANCE_OFFICER)
    analyst = mk("Analyst", "analyst@t.io", Role.EMPLOYEE, manager=mgr)

    restricted = Resource(organisation_id=org.id, name="customer_profiles",
                          resource_type=ResourceType.DATASET, owner_user_id=owner.id,
                          criticality=Criticality.CRITICAL, sensitivity=Sensitivity.RESTRICTED,
                          region="IN")
    public_ds = Resource(organisation_id=org.id, name="marketing_events",
                         resource_type=ResourceType.DATASET, owner_user_id=owner.id,
                         criticality=Criticality.LOW, sensitivity=Sensitivity.INTERNAL, region="IN")
    db.add_all([restricted, public_ds]); db.flush()

    for spec in SEED_POLICIES:
        p = Policy(organisation_id=org.id, name=spec["name"],
                   policy_type=PolicyType(spec["policy_type"]), priority=spec["priority"],
                   status=PolicyStatus.PUBLISHED, version=1)
        db.add(p); db.flush()
        v = PolicyVersion(policy_id=p.id, version_number=1, definition_json=spec["definition"])
        db.add(v); db.flush()
        p.published_version_id = v.id
    db.commit()

    ids = {"restricted": restricted.id, "public": public_ds.id,
           "analyst": analyst.email, "owner": owner.email}
    db.close()

    from app.db.session import get_db
    from app.main import app

    def override_get_db():
        s = TestingSession()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override_get_db
    c = TestClient(app)
    c.ids = ids
    yield c
    app.dependency_overrides.clear()


def _login(client, email):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "pw"})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_restricted_export_requires_approval_and_builds_workflow(client):
    h = _login(client, client.ids["analyst"])
    create = client.post("/api/v1/requests", headers=h, json={
        "request_type": "DATASET_ACCESS", "title": "Q analysis export",
        "resource_id": client.ids["restricted"],
        "payload": {"requested_action": "EXPORT", "destination_region": "US", "duration_days": 30},
    })
    assert create.status_code == 201
    rid = create.json()["id"]
    assert create.json()["status"] == "DRAFT"

    submit = client.post(f"/api/v1/requests/{rid}/submit", headers=h)
    assert submit.status_code == 200
    body = submit.json()
    assert body["status"] == "UNDER_REVIEW"
    assert body["decision"] == "REQUIRES_APPROVAL"
    assert body["risk_level"] == "CRITICAL"

    wf = client.get(f"/api/v1/requests/{rid}/workflow", headers=h).json()
    assert wf is not None
    roles = {t["approver_role"] for s in wf["stages"] for t in s["tasks"]}
    assert "DATA_OWNER" in roles
    assert "COMPLIANCE_OFFICER" in roles

    timeline = client.get(f"/api/v1/requests/{rid}/timeline", headers=h).json()
    events = {e["event_type"] for e in timeline}
    assert {"REQUEST_CREATED", "REQUEST_SUBMITTED", "POLICY_EVALUATED",
            "RISK_CALCULATED", "WORKFLOW_CREATED"} <= events


def test_clean_request_auto_approves(client):
    h = _login(client, client.ids["analyst"])
    create = client.post("/api/v1/requests", headers=h, json={
        "request_type": "DATASET_ACCESS", "title": "Read internal dataset",
        "resource_id": client.ids["public"],
        "payload": {"requested_action": "READ", "destination_region": "IN", "duration_days": 3},
    })
    rid = create.json()["id"]
    submit = client.post(f"/api/v1/requests/{rid}/submit", headers=h)
    assert submit.json()["status"] == "APPROVED"
    assert submit.json()["decision"] == "AUTO_APPROVE"


def test_owner_cannot_submit_others_request(client):
    h_analyst = _login(client, client.ids["analyst"])
    rid = client.post("/api/v1/requests", headers=h_analyst, json={
        "request_type": "DATASET_ACCESS", "title": "x", "resource_id": client.ids["public"],
        "payload": {"requested_action": "READ", "destination_region": "IN", "duration_days": 1},
    }).json()["id"]

    h_owner = _login(client, client.ids["owner"])
    resp = client.post(f"/api/v1/requests/{rid}/submit", headers=h_owner)
    assert resp.status_code == 403


def test_cancel_draft(client):
    h = _login(client, client.ids["analyst"])
    rid = client.post("/api/v1/requests", headers=h, json={
        "request_type": "DATASET_ACCESS", "title": "x", "resource_id": client.ids["public"],
        "payload": {"requested_action": "READ", "destination_region": "IN", "duration_days": 1},
    }).json()["id"]
    resp = client.post(f"/api/v1/requests/{rid}/cancel", headers=h)
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"
