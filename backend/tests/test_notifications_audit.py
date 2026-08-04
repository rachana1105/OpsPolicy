"""Tests for notifications (dedupe, retry) and SLA escalation (Milestone 6)."""
import os
from datetime import timedelta

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.db.base import Base, utcnow  # noqa: E402
import app.models  # noqa: E402,F401
from app.core.security import hash_password  # noqa: E402
from app.models.enums import (  # noqa: E402
    ApprovalTaskStatus, ExecutionMode, Role, StageStatus, WorkflowStatus,
)
from app.models.lifecycle import Notification  # noqa: E402
from app.models.org import Organisation, User  # noqa: E402
from app.models.request import (  # noqa: E402
    ApprovalStage, ApprovalTask, ApprovalWorkflow, Request,
)
from app.models.enums import RequestStatus, RequestType  # noqa: E402
from app.notifications.service import NotificationService  # noqa: E402


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    s = Session()
    org = Organisation(name="Org"); s.add(org); s.flush()
    u = User(organisation_id=org.id, name="U", email="u@t.io", role=Role.MANAGER,
             password_hash=hash_password("pw"))
    s.add(u); s.flush(); s.commit()
    s.org_id = org.id; s.user_id = u.id
    yield s
    s.close()


def test_enqueue_and_deliver(db):
    svc = NotificationService(db)
    svc.enqueue(user_id=db.user_id, notification_type="REQUEST_APPROVED",
                subject="hi", dedupe_key="k1")
    db.commit()
    sent = svc.deliver_pending(force="ok")
    db.commit()
    assert sent == 1
    note = db.query(Notification).one()
    assert note.status == "SENT"


def test_dedupe_prevents_duplicate(db):
    svc = NotificationService(db)
    n1 = svc.enqueue(user_id=db.user_id, notification_type="REQUEST_APPROVED",
                     subject="a", dedupe_key="same")
    db.commit()
    n2 = svc.enqueue(user_id=db.user_id, notification_type="REQUEST_APPROVED",
                     subject="a again", dedupe_key="same")
    db.commit()
    assert n1 is not None
    assert n2 is None
    assert db.query(Notification).count() == 1


def test_retry_then_fail(db):
    svc = NotificationService(db)
    svc.enqueue(user_id=db.user_id, notification_type="REQUEST_APPROVED",
                subject="x", dedupe_key="r")
    db.commit()
    # force failures; after MAX_ATTEMPTS the note is FAILED
    for _ in range(3):
        svc.deliver_pending(force="fail")
        db.commit()
    note = db.query(Notification).one()
    assert note.status == "FAILED"
    assert note.attempts == 3


def test_deliver_is_idempotent_after_sent(db):
    svc = NotificationService(db)
    svc.enqueue(user_id=db.user_id, notification_type="REQUEST_APPROVED",
                subject="x", dedupe_key="s")
    db.commit()
    svc.deliver_pending(force="ok"); db.commit()
    # a second delivery pass does nothing (already SENT)
    sent = svc.deliver_pending(force="ok"); db.commit()
    assert sent == 0


def test_sla_escalation_marks_and_dedupes(db):
    # Build a minimal request + workflow + overdue task.
    req = Request(organisation_id=db.org_id, request_type=RequestType.DATASET_ACCESS,
                  requester_id=db.user_id, title="t", request_payload={},
                  status=RequestStatus.UNDER_REVIEW)
    db.add(req); db.flush()
    wf = ApprovalWorkflow(request_id=req.id, status=WorkflowStatus.IN_PROGRESS, current_stage=1)
    db.add(wf); db.flush()
    stage = ApprovalStage(workflow_id=wf.id, stage_number=1, execution_mode=ExecutionMode.SEQUENTIAL,
                          minimum_approvals=1, status=StageStatus.IN_PROGRESS)
    db.add(stage); db.flush()
    task = ApprovalTask(approval_stage_id=stage.id, approver_user_id=db.user_id,
                        approver_role="MANAGER", status=ApprovalTaskStatus.PENDING,
                        due_at=utcnow() - timedelta(hours=1))
    db.add(task); db.flush(); db.commit()

    from app.workers.sla_tasks import escalate_overdue_approvals
    escalate_overdue_approvals(db); db.commit()
    db.refresh(task)
    assert task.escalated is True
    # one overdue notification enqueued
    assert db.query(Notification).filter(
        Notification.notification_type == "APPROVAL_OVERDUE").count() == 1

    # running again does not double-escalate or double-notify
    escalate_overdue_approvals(db); db.commit()
    assert db.query(Notification).filter(
        Notification.notification_type == "APPROVAL_OVERDUE").count() == 1


def test_audit_search_filters(db):
    from app.audit.service import AuditService
    audit = AuditService(db)
    audit.record(event_type="REQUEST_CREATED", entity_type="request", entity_id="r1",
                 organisation_id=db.org_id, request_id="r1", actor_id=db.user_id)
    audit.record(event_type="REQUEST_APPROVED", entity_type="request", entity_id="r1",
                 organisation_id=db.org_id, request_id="r1", actor_id=db.user_id)
    db.commit()
    all_events = audit.search(organisation_id=db.org_id)
    assert len(all_events) == 2
    approved = audit.search(organisation_id=db.org_id, event_type="REQUEST_APPROVED")
    assert len(approved) == 1
    by_request = audit.search(organisation_id=db.org_id, request_id="r1")
    assert len(by_request) == 2
