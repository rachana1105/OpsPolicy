"""Tests for policy exceptions (Milestone 5 tail)."""
import os
from datetime import timedelta

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base, utcnow  # noqa: E402
import app.models  # noqa: E402,F401
from app.core.errors import ForbiddenError, ValidationError  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.enums import (  # noqa: E402
    ExceptionStatus, RequestStatus, RequestType, Role, RiskLevel,
)
from app.models.org import Organisation, User  # noqa: E402
from app.models.request import Request  # noqa: E402
from app.services.exception_service import ExceptionService  # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    s = Session()
    org = Organisation(name="Org"); s.add(org); s.flush()

    def mk(name, email, role):
        u = User(organisation_id=org.id, name=name, email=email, role=role,
                 password_hash=hash_password("pw"))
        s.add(u); s.flush(); return u

    requester = mk("Req", "req@t.io", Role.EMPLOYEE)
    manager = mk("Mgr", "mgr@t.io", Role.MANAGER)
    security = mk("Sec", "sec@t.io", Role.SECURITY_REVIEWER)
    s.commit()
    s.org_id = org.id
    s.requester = requester; s.manager = manager; s.security = security
    yield s
    s.close()


def _make_request(db, risk=RiskLevel.MEDIUM, expires_in_days=10):
    req = Request(organisation_id=db.org_id, request_type=RequestType.DATASET_ACCESS,
                  requester_id=db.requester.id, title="t", request_payload={},
                  status=RequestStatus.ACTIVE, risk_level=risk,
                  expires_at=utcnow() + timedelta(days=expires_in_days))
    db.add(req); db.flush(); db.commit()
    return req


def test_exception_requires_expiry_after_start(db):
    req = _make_request(db)
    svc = ExceptionService(db)
    now = utcnow()
    with pytest.raises(ValidationError):
        svc.request_exception(
            request_id=req.id, actor=db.requester, policy_id=None,
            justification="j", risk_description=None, compensating_controls=None,
            start_at=now, expires_at=now - timedelta(hours=1))


def test_exception_cannot_outlive_request(db):
    req = _make_request(db, expires_in_days=5)
    svc = ExceptionService(db)
    now = utcnow()
    with pytest.raises(ValidationError):
        svc.request_exception(
            request_id=req.id, actor=db.requester, policy_id=None,
            justification="j", risk_description=None, compensating_controls=None,
            start_at=now, expires_at=now + timedelta(days=10))  # beyond request


def test_requester_cannot_approve_own(db):
    req = _make_request(db)
    svc = ExceptionService(db)
    now = utcnow()
    exc = svc.request_exception(
        request_id=req.id, actor=db.requester, policy_id=None,
        justification="j", risk_description=None, compensating_controls=None,
        start_at=now, expires_at=now + timedelta(days=2))
    db.commit()
    with pytest.raises(ForbiddenError):
        svc.approve(exception_id=exc.id, actor=db.requester)


def test_high_risk_requires_security_or_compliance(db):
    req = _make_request(db, risk=RiskLevel.CRITICAL)
    svc = ExceptionService(db)
    now = utcnow()
    exc = svc.request_exception(
        request_id=req.id, actor=db.requester, policy_id=None,
        justification="j", risk_description="high", compensating_controls="mfa",
        start_at=now, expires_at=now + timedelta(days=2))
    db.commit()
    # manager cannot approve a high-risk exception
    with pytest.raises(ForbiddenError):
        svc.approve(exception_id=exc.id, actor=db.manager)
    # security can
    approved = svc.approve(exception_id=exc.id, actor=db.security)
    db.commit()
    assert approved.status in (ExceptionStatus.ACTIVE, ExceptionStatus.APPROVED)


def test_approve_activates_when_in_window(db):
    req = _make_request(db)
    svc = ExceptionService(db)
    now = utcnow()
    exc = svc.request_exception(
        request_id=req.id, actor=db.requester, policy_id=None,
        justification="j", risk_description=None, compensating_controls=None,
        start_at=now - timedelta(minutes=1), expires_at=now + timedelta(days=2))
    db.commit()
    approved = svc.approve(exception_id=exc.id, actor=db.manager)
    db.commit()
    assert approved.status == ExceptionStatus.ACTIVE


def test_expire_worker_marks_expired(db):
    req = _make_request(db)
    svc = ExceptionService(db)
    now = utcnow()
    exc = svc.request_exception(
        request_id=req.id, actor=db.requester, policy_id=None,
        justification="j", risk_description=None, compensating_controls=None,
        start_at=now - timedelta(days=1), expires_at=now + timedelta(days=1))
    db.commit()
    svc.approve(exception_id=exc.id, actor=db.manager); db.commit()
    # force expiry
    exc.expires_at = now - timedelta(minutes=1)
    db.commit()
    from app.workers.exception_tasks import expire_exceptions
    expire_exceptions(db); db.commit()
    db.refresh(exc)
    assert exc.status == ExceptionStatus.EXPIRED


def test_activate_worker_moves_approved_to_active(db):
    req = _make_request(db)
    svc = ExceptionService(db)
    now = utcnow()
    # start in the future so approve() leaves it APPROVED, not ACTIVE
    exc = svc.request_exception(
        request_id=req.id, actor=db.requester, policy_id=None,
        justification="j", risk_description=None, compensating_controls=None,
        start_at=now + timedelta(hours=1), expires_at=now + timedelta(days=2))
    db.commit()
    svc.approve(exception_id=exc.id, actor=db.manager); db.commit()
    db.refresh(exc)
    assert exc.status == ExceptionStatus.APPROVED
    # move start into the past, run activation worker
    exc.start_at = now - timedelta(minutes=1)
    db.commit()
    from app.workers.exception_tasks import activate_due_exceptions
    activate_due_exceptions(db); db.commit()
    db.refresh(exc)
    assert exc.status == ExceptionStatus.ACTIVE
