"""Tests for provisioning, expiry, and revocation (Milestone 5)."""
import os
from datetime import timedelta

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REVOCATION_RETRY_DELAYS", "1,1,1")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base, utcnow  # noqa: E402
import app.models  # noqa: E402,F401
from app.core.security import hash_password  # noqa: E402
from app.models.enums import (  # noqa: E402
    Criticality, GrantType, ProvisioningStatus, RequestStatus, RequestType,
    ResourceType, RevocationStatus, Role, Sensitivity,
)
from app.models.lifecycle import AccessGrant, RevocationAttempt  # noqa: E402
from app.models.org import Organisation, Resource, User  # noqa: E402
from app.models.request import Request  # noqa: E402
from app.provisioning.lifecycle import AccessLifecycleService  # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    s = Session()
    org = Organisation(name="Org"); s.add(org); s.flush()
    analyst = User(organisation_id=org.id, name="A", email="a@t.io", role=Role.EMPLOYEE,
                   password_hash=hash_password("pw"))
    s.add(analyst); s.flush()
    res = Resource(organisation_id=org.id, name="ds", resource_type=ResourceType.DATASET,
                   criticality=Criticality.HIGH, sensitivity=Sensitivity.RESTRICTED, region="IN")
    s.add(res); s.flush()
    s.commit()
    s.org_id = org.id; s.analyst_id = analyst.id; s.res_id = res.id
    yield s
    s.close()


def _approved_request(db, duration=7):
    req = Request(
        organisation_id=db.org_id, request_type=RequestType.DATASET_ACCESS,
        requester_id=db.analyst_id, resource_id=db.res_id, title="t",
        request_payload={"requested_action": "READ", "duration_days": duration},
        status=RequestStatus.APPROVED,
    )
    db.add(req); db.flush(); db.commit()
    return req


def test_provision_creates_active_grant_with_expiry(db):
    req = _approved_request(db, duration=7)
    svc = AccessLifecycleService(db)
    grant = svc.provision_request(req, force_outcome="succeed")
    db.commit()
    assert grant.provisioning_status == ProvisioningStatus.SUCCEEDED
    assert grant.grant_type == GrantType.GRANT_DATASET_READ
    assert grant.expires_at is not None
    assert req.status == RequestStatus.ACTIVE


def test_provision_is_idempotent(db):
    req = _approved_request(db)
    svc = AccessLifecycleService(db)
    g1 = svc.provision_request(req, force_outcome="succeed"); db.commit()
    # second call returns the same grant, no duplicate
    g2 = svc.provision_request(req, force_outcome="succeed"); db.commit()
    assert g1.id == g2.id
    count = db.query(AccessGrant).filter(AccessGrant.request_id == req.id).count()
    assert count == 1


def test_expiry_and_successful_revocation(db):
    req = _approved_request(db)
    svc = AccessLifecycleService(db)
    grant = svc.provision_request(req, force_outcome="succeed"); db.commit()
    # force expiry in the past
    grant.expires_at = utcnow() - timedelta(seconds=1)
    db.commit()
    svc.mark_expiring(grant); db.commit()
    assert req.status == RequestStatus.EXPIRING
    svc.attempt_revocation(grant, force_outcome="succeed"); db.commit()
    assert grant.revocation_status == RevocationStatus.SUCCEEDED
    assert req.status == RequestStatus.REVOKED


def test_revocation_retry_then_escalate(db):
    req = _approved_request(db)
    svc = AccessLifecycleService(db)  # retry delays "1,1,1" -> 3 retries then escalate
    grant = svc.provision_request(req, force_outcome="succeed"); db.commit()
    svc.mark_expiring(grant); db.commit()

    # Attempts 1..3 fail and schedule retries.
    for n in range(1, 4):
        svc.attempt_revocation(grant, force_outcome="fail"); db.commit()
        assert grant.revocation_status == RevocationStatus.FAILED

    # 4th attempt exhausts retries -> escalate.
    svc.attempt_revocation(grant, force_outcome="fail"); db.commit()
    assert grant.revocation_status == RevocationStatus.ESCALATED
    assert req.status == RequestStatus.ESCALATED
    attempts = db.query(RevocationAttempt).filter(
        RevocationAttempt.access_grant_id == grant.id).count()
    assert attempts == 4


def test_successful_revocation_is_terminal(db):
    req = _approved_request(db)
    svc = AccessLifecycleService(db)
    grant = svc.provision_request(req, force_outcome="succeed"); db.commit()
    svc.mark_expiring(grant); db.commit()
    svc.attempt_revocation(grant, force_outcome="succeed"); db.commit()
    # a second revocation attempt must be refused
    from app.core.errors import ConflictError
    with pytest.raises(ConflictError):
        svc.attempt_revocation(grant, force_outcome="succeed")


def test_worker_duplicate_run_no_double_grant(db):
    """Running the provision task twice must not create two grants."""
    _approved_request(db)
    from app.workers.lifecycle_tasks import provision_approved_requests
    provision_approved_requests(db)
    provision_approved_requests(db)
    grants = db.query(AccessGrant).count()
    assert grants == 1


def test_worker_expiry_query_matches_expired_grants(db):
    """Regression: the expiry worker must actually select expired grants.

    A datetime storage/comparison mismatch previously made this query return
    nothing on SQLite, so grants never expired. This drives the worker tasks
    end to end against a grant whose expiry is in the past.
    """
    req = _approved_request(db)
    svc = AccessLifecycleService(db)
    grant = svc.provision_request(req, force_outcome="succeed"); db.commit()
    # expire it
    grant.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()

    from app.workers.lifecycle_tasks import schedule_access_expiry
    schedule_access_expiry(db); db.commit()
    assert grant.revocation_status == RevocationStatus.IN_PROGRESS  # worker picked it up
    # complete revocation deterministically
    svc.attempt_revocation(grant, force_outcome="succeed"); db.commit()
    assert grant.revocation_status == RevocationStatus.SUCCEEDED
    assert req.status == RequestStatus.REVOKED


def test_duration_capped_by_policy_evaluation(db):
    # Request asks 30 days but a stored evaluation caps at 7.
    req = _approved_request(db, duration=30)
    from app.models.request import PolicyEvaluation
    db.add(PolicyEvaluation(
        request_id=req.id, policy_id="p", policy_version_id="v", matched=True,
        result={}, violations=[], required_actions=[{"type": "SET_MAXIMUM_DURATION", "days": 7}],
        risk_contribution=0, evaluated_at=utcnow(),
    ))
    db.commit()
    svc = AccessLifecycleService(db)
    grant = svc.provision_request(req, force_outcome="succeed"); db.commit()
    span_days = (grant.expires_at - grant.granted_at).days
    assert span_days == 7
