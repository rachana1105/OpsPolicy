"""Notification service (Milestone 6).

Enqueues notifications with a dedupe key so the same event never notifies twice,
and delivers them through a mock provider with a bounded retry. Enqueue and
deliver are separate steps: services enqueue synchronously; a worker delivers
and retries out of band.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.lifecycle import Notification
from app.notifications.provider import MockNotificationProvider

log = get_logger("notifications")

MAX_ATTEMPTS = 3

# Canonical notification types (spec).
NOTIFICATION_TYPES = {
    "APPROVAL_ASSIGNED",
    "APPROVAL_OVERDUE",
    "REQUEST_APPROVED",
    "REQUEST_REJECTED",
    "ACCESS_GRANTED",
    "ACCESS_EXPIRING",
    "ACCESS_REVOKED",
    "REVOCATION_FAILED",
    "EXCEPTION_EXPIRING",
    "POLICY_SIMULATION_COMPLETED",
}


class NotificationService:
    def __init__(self, db: Session):
        self.db = db
        self.provider = MockNotificationProvider()

    def enqueue(
        self,
        *,
        user_id: str,
        notification_type: str,
        subject: str,
        body: str | None = None,
        dedupe_key: str | None = None,
    ) -> Notification | None:
        """Create a pending notification. Returns None if deduped away."""
        if dedupe_key:
            existing = self.db.execute(
                select(Notification).where(Notification.dedupe_key == dedupe_key)
            ).scalar_one_or_none()
            if existing:
                return None  # already enqueued for this event

        note = Notification(
            user_id=user_id, notification_type=notification_type, subject=subject,
            body=body, status="PENDING", attempts=0, dedupe_key=dedupe_key,
        )
        self.db.add(note)
        try:
            self.db.flush()
        except IntegrityError:
            # Concurrent insert with the same dedupe_key — treat as deduped.
            self.db.rollback()
            return None
        return note

    def deliver_pending(self, *, limit: int = 50, force: str | None = None) -> int:
        """Attempt delivery for PENDING/RETRYING notifications. Returns count sent."""
        notes = self.db.execute(
            select(Notification)
            .where(Notification.status.in_(["PENDING", "RETRYING"]))
            .limit(limit)
        ).scalars().all()

        sent = 0
        for note in notes:
            note.attempts += 1
            result = self.provider.send(
                notification_id=note.id, user_id=note.user_id,
                subject=note.subject, body=note.body, force=force,
            )
            if result.delivered:
                note.status = "SENT"
                sent += 1
            elif note.attempts >= MAX_ATTEMPTS:
                note.status = "FAILED"
                log.error("notification_failed", id=note.id, attempts=note.attempts)
            else:
                note.status = "RETRYING"
        self.db.flush()
        return sent

    def list_for_user(self, user_id: str, *, limit: int = 50) -> list[Notification]:
        return list(self.db.execute(
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        ).scalars().all())
