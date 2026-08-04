"""Integration + concurrency tests for the approval decision engine (M4)."""
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
def env():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)

    db = Session()
    org = Organisation(name="TestOrg"); db.add(org); db.flush()

    def mk(name, email, role, emp=EmployeeType.EMPLOYEE, manager=None):
        u = User(organisation_id=org.id, name=name, email=email, role=role,
                 employee_type=emp, manager_id=manager.id if manager else None,
                 password_hash=hash_password("pw"))
        db.add(u); db.flush(); return u

    mgr = mk("Mgr", "mgr@t.io", Role.MANAGER)
    owner = mk("Owner", "owner@t.io", Role.DATA_OWNER)
    comp = mk("Comp", "comp@t.io", Role.COMPLIANCE_OFFICER)
    comp2 = mk("Comp2", "comp2@t.io", Role.COMPLIANCE_OFFICER)
    analyst = mk("Analyst", "analyst@t.io", Role.EMPLOYEE, manager=mgr)
    admin = mk("Admin", "admin@t.io", Role.PLATFORM_ADMIN)

    restricted = Resource(organisation_id=org.id, name="customer_profiles",
                          resource_type=ResourceType.DATASET, owner_user_id=owner.id,
                          criticality=Criticality.CRITICAL, sensitivity=Sensitivity.RESTRICTED,
                          region="IN")
    db.add(restricted); db.flush()

    for spec in SEED_POLICIES:
        p = Policy(organisation_id=org.id, name=spec["name"],
                   policy_type=PolicyType(spec["policy_type"]), priority=spec["priority"],
                   status=PolicyStatus.PUBLISHED, version=1)
        db.add(p); db.flush()
        v = PolicyVersion(policy_id=p.id, version_number=1, definition_json=spec["definition"])
        db.add(v); db.flush()
        p.published_version_id = v.id
    db.commit()

    ids = {"restricted": restricted.id, "analyst": "analyst@t.io", "owner": "owner@t.io",
           "comp": "comp@t.io", "comp2": "comp2@t.io", "admin": "admin@t.io",
           "owner_id": owner.id, "comp_id": comp.id}
    db.close()

    from app.db.session import get_db
    from app.main import app

    def override():
        s = Session()
        try:
            yield s
        finally:
            s.close()

    app.dependency_overrides[get_db] = override
    c = TestClient(app)
    c.ids = ids
    c.Session = Session
    yield c
    app.dependency_overrides.clear()


def login(client, email):
    r = client.post("/api/v1/auth/login", json={"email": email, "password": "pw"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def submit_restricted(client):
    h = login(client, client.ids["analyst"])
    rid = client.post("/api/v1/requests", headers=h, json={
        "request_type": "DATASET_ACCESS", "title": "export",
        "resource_id": client.ids["restricted"],
        "payload": {"requested_action": "EXPORT", "destination_region": "US", "duration_days": 30},
    }).json()["id"]
    client.post(f"/api/v1/requests/{rid}/submit", headers=h)
    return rid


def test_inbox_shows_assigned_tasks(env):
    submit_restricted(env)
    h_owner = login(env, env.ids["owner"])
    inbox = env.get("/api/v1/approvals/inbox", headers=h_owner).json()
    assert len(inbox) == 1
    assert inbox[0]["approver_role"] == "DATA_OWNER"
    assert inbox[0]["risk_level"] == "CRITICAL"


def test_full_approval_reaches_approved(env):
    rid = submit_restricted(env)
    # Stage 2 is parallel: DATA_OWNER + COMPLIANCE_OFFICER, min 2.
    owner_task = env.get("/api/v1/approvals/inbox", headers=login(env, env.ids["owner"])).json()[0]
    comp_task = env.get("/api/v1/approvals/inbox", headers=login(env, env.ids["comp"])).json()[0]

    r1 = env.post(f"/api/v1/approvals/{owner_task['task_id']}/decision",
                  headers=login(env, env.ids["owner"]),
                  json={"operation_id": "op-1", "decision": "APPROVE"})
    assert r1.status_code == 200
    # After one approval, request still not approved.
    assert env.get(f"/api/v1/requests/{rid}", headers=login(env, env.ids["analyst"])).json()["status"] != "APPROVED"

    r2 = env.post(f"/api/v1/approvals/{comp_task['task_id']}/decision",
                  headers=login(env, env.ids["comp"]),
                  json={"operation_id": "op-2", "decision": "APPROVE"})
    assert r2.status_code == 200
    final = env.get(f"/api/v1/requests/{rid}", headers=login(env, env.ids["analyst"])).json()
    assert final["status"] == "APPROVED"


def test_self_approval_blocked(env):
    # analyst is requester; give them a compliance task illegitimately -> can't, so
    # instead verify requester can't act on any task in their request.
    submit_restricted(env)
    owner_task = env.get("/api/v1/approvals/inbox", headers=login(env, env.ids["owner"])).json()[0]
    # analyst tries to approve the owner's task
    resp = env.post(f"/api/v1/approvals/{owner_task['task_id']}/decision",
                    headers=login(env, env.ids["analyst"]),
                    json={"operation_id": "op-x", "decision": "APPROVE"})
    assert resp.status_code in (403, 404)


def test_idempotent_decision(env):
    submit_restricted(env)
    owner_task = env.get("/api/v1/approvals/inbox", headers=login(env, env.ids["owner"])).json()[0]
    h = login(env, env.ids["owner"])
    r1 = env.post(f"/api/v1/approvals/{owner_task['task_id']}/decision", headers=h,
                  json={"operation_id": "same-op", "decision": "APPROVE"})
    r2 = env.post(f"/api/v1/approvals/{owner_task['task_id']}/decision", headers=h,
                  json={"operation_id": "same-op", "decision": "APPROVE"})
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json()["status"] == r2.json()["status"] == "APPROVED"


def test_rejection_rejects_request(env):
    rid = submit_restricted(env)
    owner_task = env.get("/api/v1/approvals/inbox", headers=login(env, env.ids["owner"])).json()[0]
    env.post(f"/api/v1/approvals/{owner_task['task_id']}/decision",
             headers=login(env, env.ids["owner"]),
             json={"operation_id": "rej", "decision": "REJECT", "comment": "no"})
    final = env.get(f"/api/v1/requests/{rid}", headers=login(env, env.ids["analyst"])).json()
    assert final["status"] == "REJECTED"


def test_optimistic_lock_conflict(env):
    submit_restricted(env)
    owner_task = env.get("/api/v1/approvals/inbox", headers=login(env, env.ids["owner"])).json()[0]
    h = login(env, env.ids["owner"])
    # First decision succeeds and bumps version.
    env.post(f"/api/v1/approvals/{owner_task['task_id']}/decision", headers=h,
             json={"operation_id": "v1", "decision": "APPROVE",
                   "expected_version": owner_task["lock_version"]})
    # Second, different op, with the stale version -> conflict.
    resp = env.post(f"/api/v1/approvals/{owner_task['task_id']}/decision", headers=h,
                    json={"operation_id": "v2", "decision": "REJECT",
                          "expected_version": owner_task["lock_version"]})
    assert resp.status_code == 409


def test_concurrent_approvers_single_transition(env):
    """Simulate two approvers acting on the same task from stale reads.

    Rather than rely on OS thread timing over SQLite's single connection, this
    drives the optimistic-lock guard directly: both actors read the same
    lock_version, the first decision commits and bumps it, and the second — still
    holding the stale version — is rejected. Exactly one transition sticks.
    """
    submit_restricted(env)
    owner_task = env.get("/api/v1/approvals/inbox",
                         headers=login(env, env.ids["owner"])).json()[0]
    h = login(env, env.ids["owner"])
    seen_version = owner_task["lock_version"]

    first = env.post(f"/api/v1/approvals/{owner_task['task_id']}/decision", headers=h,
                     json={"operation_id": "race-a", "decision": "APPROVE",
                           "expected_version": seen_version})
    second = env.post(f"/api/v1/approvals/{owner_task['task_id']}/decision", headers=h,
                      json={"operation_id": "race-b", "decision": "REJECT",
                            "expected_version": seen_version})

    assert first.status_code == 200
    assert second.status_code == 409  # stale version rejected

    final = env.get(f"/api/v1/approvals/{owner_task['task_id']}", headers=h).json()
    assert final["status"] == "APPROVED"
    assert final["decision"] == "APPROVE"
