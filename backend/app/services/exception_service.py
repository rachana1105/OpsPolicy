"""Policy exception management (Milestone 5 tail).

A temporary, justified override of a policy with compensating controls and a hard
expiry. Enforces the spec's rules:

  * Exceptions MUST have an expiry time (no permanent exceptions).
  * An exception cannot outlive its parent request's expiry.
  * The requester cannot approve their own exception.
  * High-risk requests' exceptions require security or compliance approval.
  * Expired exceptions become inactive automatically (a worker task).
  * Activation and expiry generate audit events.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.db.base import utcnow
from app.models.enums import ExceptionStatus, RequestStatus, Role, RiskLevel
from app.models.lifecycle import PolicyException
from app.models.org import User
from app.models.request import Request
from app.notifications.service import NotificationService

# Roles allowed to approve a high-risk exception.
HIGH_RISK_APPROVER_ROLES = {Role.SECURITY_REVIEWER.value, Role.COMPLIANCE_OFFICER.value,
                            Role.PLATFORM_ADMIN.value}


class ExceptionService:
    def __init__(self, db: Session, request_id_header: str | None = None):
        self.db = db
        self.audit = AuditService(db)
        self.notifications = NotificationService(db)
        self.request_id_header = request_id_header

    def _request(self, request_id: str, org_id: str) -> Request:
        req = self.db.get(Request, request_id)
        if not req or req.organisation_id != org_id:
            raise NotFoundError("Request not found.")
        return req

    def request_exception(
        self,
        *,
        request_id: str,
        actor: User,
        policy_id: str | None,
        justification: str,
        risk_description: str | None,
        compensating_controls: str | None,
        start_at: datetime,
        expires_at: datetime,
    ) -> PolicyException:
        req = self._request(request_id, actor.organisation_id)

        # Rule: must have an expiry, and it must be after the start.
        if expires_at is None:
            raise ValidationError("An exception must have an expiry time.")
        if expires_at <= start_at:
            raise ValidationError("Exception expiry must be after its start time.")

        # Rule: cannot outlive the parent request.
        if req.expires_at and expires_at > req.expires_at:
            raise ValidationError(
                "An exception cannot outlive its parent request.",
                details={"request_expires_at": req.expires_at.isoformat(),
                         "exception_expires_at": expires_at.isoformat()},
            )

        exc = PolicyException(
            request_id=request_id, policy_id=policy_id, requested_by=actor.id,
            justification=justification, risk_description=risk_description,
            compensating_controls=compensating_controls, start_at=start_at,
            expires_at=expires_at, status=ExceptionStatus.REQUESTED,
        )
        self.db.add(exc)
        self.db.flush()
        self.audit.record(
            event_type="EXCEPTION_REQUESTED", entity_type="policy_exception",
            entity_id=exc.id, organisation_id=req.organisation_id, request_id=request_id,
            actor_id=actor.id, new_state=ExceptionStatus.REQUESTED.value,
            request_id_header=self.request_id_header,
        )
        return exc

    def approve(self, *, exception_id: str, actor: User) -> PolicyException:
        # TODO: guard rails (exception in REQUESTED/UNDER_REVIEW, requester
        # can't approve their own exception, HIGH/CRITICAL risk requests
        # require a security/compliance approver role); then mark the
        # exception ACTIVE (if within its start/expiry window) or APPROVED,
        # audit, and notify the requester.
        raise NotImplementedError

    def reject(self, *, exception_id: str, actor: User, reason: str | None = None) -> PolicyException:
        exc = self.db.get(PolicyException, exception_id)
        if not exc:
            raise NotFoundError("Exception not found.")
        req = self._request(exc.request_id, actor.organisation_id)
        if exc.status not in (ExceptionStatus.REQUESTED, ExceptionStatus.UNDER_REVIEW):
            raise ConflictError("This exception can no longer be rejected.")
        if exc.requested_by == actor.id:
            raise ForbiddenError("You cannot reject your own exception.")
        exc.status = ExceptionStatus.REJECTED
        self.audit.record(
            event_type="EXCEPTION_REJECTED", entity_type="policy_exception",
            entity_id=exc.id, organisation_id=req.organisation_id, request_id=exc.request_id,
            actor_id=actor.id, new_state=ExceptionStatus.REJECTED.value,
            payload={"reason": reason}, request_id_header=self.request_id_header,
        )
        self.db.flush()
        return exc

    def revoke(self, *, exception_id: str, actor: User) -> PolicyException:
        exc = self.db.get(PolicyException, exception_id)
        if not exc:
            raise NotFoundError("Exception not found.")
        req = self._request(exc.request_id, actor.organisation_id)
        if exc.status not in (ExceptionStatus.APPROVED, ExceptionStatus.ACTIVE):
            raise ConflictError("Only an active or approved exception can be revoked.")
        exc.status = ExceptionStatus.REVOKED
        exc.revoked_at = utcnow()
        self.audit.record(
            event_type="EXCEPTION_REVOKED", entity_type="policy_exception",
            entity_id=exc.id, organisation_id=req.organisation_id, request_id=exc.request_id,
            actor_id=actor.id, new_state=ExceptionStatus.REVOKED.value,
            request_id_header=self.request_id_header,
        )
        self.db.flush()
        return exc

    def list_for_org(self, organisation_id: str, *, status: str | None = None) -> list[PolicyException]:
        stmt = (
            select(PolicyException)
            .join(Request, PolicyException.request_id == Request.id)
            .where(Request.organisation_id == organisation_id)
            .order_by(PolicyException.created_at.desc())
        )
        if status:
            stmt = stmt.where(PolicyException.status == ExceptionStatus(status))
        return list(self.db.execute(stmt).scalars().all())

    def list_for_request(self, request_id: str) -> list[PolicyException]:
        return list(self.db.execute(
            select(PolicyException).where(PolicyException.request_id == request_id)
            .order_by(PolicyException.created_at.desc())
        ).scalars().all())
