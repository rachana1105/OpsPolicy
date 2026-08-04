"""Exception lifecycle worker tasks (Milestone 5 tail + 6).

activate_due_exceptions: move APPROVED exceptions into ACTIVE once their start
time arrives.

expire_exceptions: move ACTIVE/APPROVED exceptions to EXPIRED once past their
expiry, and notify the requester. Idempotent — an already-expired exception is
skipped.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.core.logging import get_logger
from app.db.base import utcnow
from app.models.enums import ExceptionStatus
from app.models.lifecycle import PolicyException
from app.models.request import Request
from app.notifications.service import NotificationService

log = get_logger("worker.exceptions")


def activate_due_exceptions(db: Session) -> None:
    now = utcnow()
    due = db.execute(
        select(PolicyException).where(
            PolicyException.status == ExceptionStatus.APPROVED,
            PolicyException.start_at <= now,
            PolicyException.expires_at > now,
        )
    ).scalars().all()
    audit = AuditService(db)
    for exc in due:
        req = db.get(Request, exc.request_id)
        exc.status = ExceptionStatus.ACTIVE
        audit.record(
            event_type="EXCEPTION_ACTIVATED", entity_type="policy_exception",
            entity_id=exc.id, organisation_id=req.organisation_id if req else None,
            request_id=exc.request_id, new_state=ExceptionStatus.ACTIVE.value,
        )
        log.info("exception_activated", exception_id=exc.id)


def expire_exceptions(db: Session) -> None:
    now = utcnow()
    expiring = db.execute(
        select(PolicyException).where(
            PolicyException.status.in_([ExceptionStatus.ACTIVE, ExceptionStatus.APPROVED]),
            PolicyException.expires_at <= now,
        )
    ).scalars().all()
    audit = AuditService(db)
    notifications = NotificationService(db)
    for exc in expiring:
        req = db.get(Request, exc.request_id)
        exc.status = ExceptionStatus.EXPIRED
        audit.record(
            event_type="EXCEPTION_EXPIRED", entity_type="policy_exception",
            entity_id=exc.id, organisation_id=req.organisation_id if req else None,
            request_id=exc.request_id, new_state=ExceptionStatus.EXPIRED.value,
        )
        notifications.enqueue(
            user_id=exc.requested_by, notification_type="EXCEPTION_EXPIRING",
            subject="A policy exception has expired",
            dedupe_key=f"EXCEPTION_EXPIRED:{exc.id}",
        )
        log.info("exception_expired", exception_id=exc.id)


def register(runner_register) -> None:
    runner_register("activate_due_exceptions")(activate_due_exceptions)
    runner_register("expire_exceptions")(expire_exceptions)
