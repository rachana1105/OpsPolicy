"""Background lifecycle tasks (Milestone 5).

Each task is idempotent and safe to run repeatedly. They are registered with the
worker runner and executed every tick. A Redis-based lock guards per-grant work
so duplicate worker processes cannot revoke the same grant twice; when Redis is
unavailable the DB-level guards (terminal revocation status, unique grant key)
still prevent double side effects.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.base import utcnow
from app.models.enums import ProvisioningStatus, RequestStatus, RevocationStatus
from app.models.lifecycle import AccessGrant, RevocationAttempt
from app.models.request import Request
from app.provisioning.lifecycle import AccessLifecycleService
from app.workers.locks import grant_lock

log = get_logger("worker.lifecycle")


def provision_approved_requests(db: Session) -> None:
    """Provision every APPROVED request that has no successful grant yet."""
    approved = db.execute(
        select(Request).where(Request.status == RequestStatus.APPROVED)
    ).scalars().all()
    for req in approved:
        with grant_lock(f"provision:{req.id}") as acquired:
            if not acquired:
                continue
            svc = AccessLifecycleService(db)
            try:
                svc.provision_request(req)
                db.commit()
                log.info("provisioned", request_id=req.id)
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                log.error("provision_failed", request_id=req.id, error=str(exc))


def schedule_access_expiry(db: Session) -> None:
    """Move ACTIVE grants whose expiry has passed into the EXPIRING state."""
    now = utcnow()
    grants = db.execute(
        select(AccessGrant).where(
            AccessGrant.provisioning_status == ProvisioningStatus.SUCCEEDED,
            AccessGrant.revocation_status == RevocationStatus.PENDING,
            AccessGrant.expires_at.isnot(None),
            AccessGrant.expires_at <= now,
        )
    ).scalars().all()
    for grant in grants:
        with grant_lock(f"expire:{grant.id}") as acquired:
            if not acquired:
                continue
            svc = AccessLifecycleService(db)
            try:
                svc.mark_expiring(grant)
                db.commit()
                log.info("marked_expiring", grant_id=grant.id)
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                log.error("expire_failed", grant_id=grant.id, error=str(exc))


def revoke_expired_access(db: Session) -> None:
    """Attempt revocation for grants in the IN_PROGRESS (just-expired) state."""
    grants = db.execute(
        select(AccessGrant).where(
            AccessGrant.revocation_status == RevocationStatus.IN_PROGRESS
        )
    ).scalars().all()
    for grant in grants:
        with grant_lock(f"revoke:{grant.id}") as acquired:
            if not acquired:
                continue
            svc = AccessLifecycleService(db)
            try:
                svc.attempt_revocation(grant)
                db.commit()
                log.info("revocation_attempted", grant_id=grant.id)
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                log.error("revoke_failed", grant_id=grant.id, error=str(exc))


def retry_failed_revocations(db: Session) -> None:
    """Re-attempt revocation for FAILED grants whose next_retry_at has arrived."""
    now = utcnow()
    grants = db.execute(
        select(AccessGrant).where(
            AccessGrant.revocation_status == RevocationStatus.FAILED
        )
    ).scalars().all()
    for grant in grants:
        latest = db.execute(
            select(RevocationAttempt)
            .where(RevocationAttempt.access_grant_id == grant.id)
            .order_by(RevocationAttempt.attempt_number.desc())
        ).scalars().first()
        if not latest or not latest.next_retry_at or latest.next_retry_at > now:
            continue
        with grant_lock(f"revoke:{grant.id}") as acquired:
            if not acquired:
                continue
            svc = AccessLifecycleService(db)
            try:
                svc.attempt_revocation(grant)
                db.commit()
                log.info("revocation_retried", grant_id=grant.id)
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                log.error("retry_failed", grant_id=grant.id, error=str(exc))


def register(runner_register) -> None:
    """Register all lifecycle tasks with the worker runner."""
    runner_register("provision_approved_requests")(provision_approved_requests)
    runner_register("schedule_access_expiry")(schedule_access_expiry)
    runner_register("revoke_expired_access")(revoke_expired_access)
    runner_register("retry_failed_revocations")(retry_failed_revocations)
