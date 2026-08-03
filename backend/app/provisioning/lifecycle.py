"""Access lifecycle orchestration (Milestone 5).

Provisions an approved request into an AccessGrant, computes its expiry from the
policy-approved duration, and drives the expiry/revocation state machine with a
configurable backoff-and-escalate ladder.

Grant lifecycle:
    APPROVED request -> PROVISIONING -> ACTIVE grant (expiry scheduled)
                     -> EXPIRING (expiry reached)
                     -> revocation attempt -> REVOKED
                                           -> REVOCATION_FAILED -> retry / ESCALATED

Idempotency: provisioning is guarded by the AccessGrant unique key
(request_id, grant_type, resource_id, user_id). Revocation is guarded so a
successful revocation is terminal and duplicate scheduled jobs cannot revoke
twice.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.core.config import settings
from app.core.errors import ConflictError, NotFoundError
from app.db.base import utcnow
from app.models.enums import (
    GrantType,
    ProvisioningStatus,
    RequestStatus,
    RevocationStatus,
)
from app.models.lifecycle import AccessGrant, RevocationAttempt
from app.models.request import Request
from app.provisioning.service import SimulatedProvisioningService, grant_type_for
from app.workflow.transitions import assert_transition
from app.notifications.service import NotificationService

# Default duration (days) when a request carries none and no policy cap applies.
DEFAULT_DURATION_DAYS = 7


class AccessLifecycleService:
    def __init__(self, db: Session, request_id_header: str | None = None):
        self.db = db
        self.audit = AuditService(db)
        self.provisioner = SimulatedProvisioningService()
        self.notifications = NotificationService(db)
        self.request_id_header = request_id_header
        self.retry_delays = settings.revocation_retry_delay_list  # seconds

    # ---- provisioning ----

    def _effective_duration_days(self, req: Request) -> int:
        """Requested duration, capped by any policy maximum recorded on evaluation."""
        requested = req.request_payload.get("duration_days")
        # Look for the strictest SET_MAXIMUM_DURATION among stored evaluations.
        from app.models.request import PolicyEvaluation
        evals = self.db.execute(
            select(PolicyEvaluation).where(PolicyEvaluation.request_id == req.id)
        ).scalars().all()
        max_cap = None
        for e in evals:
            for action in e.required_actions or []:
                if action.get("type") == "SET_MAXIMUM_DURATION":
                    days = int(action["days"])
                    max_cap = days if max_cap is None else min(max_cap, days)
        if isinstance(requested, (int, float)):
            requested = int(requested)
        else:
            requested = max_cap or DEFAULT_DURATION_DAYS
        if max_cap is not None:
            return min(requested, max_cap)
        return requested

    def provision_request(self, req: Request, *, force_outcome: str | None = None) -> AccessGrant:
        """Provision an APPROVED request. Idempotent on the grant unique key."""
        # TODO: idempotency check against an existing successful grant; move
        # the request APPROVED -> PROVISIONING; create/reuse the AccessGrant
        # row; call self.provisioner.provision(...); on success, mark the
        # grant SUCCEEDED with an expiry (via _effective_duration_days),
        # move the request to ACTIVE, audit + notify; on failure, mark the
        # grant FAILED/RETRYING and the request REVOCATION_FAILED.
        raise NotImplementedError

    # ---- expiry + revocation ----

    def mark_expiring(self, grant: AccessGrant) -> None:
        req = self.db.get(Request, grant.request_id)
        if req.status == RequestStatus.ACTIVE:
            assert_transition(req.status, RequestStatus.EXPIRING)
            req.status = RequestStatus.EXPIRING
            req.lock_version += 1
        grant.revocation_status = RevocationStatus.IN_PROGRESS
        grant.lock_version += 1
        self.audit.record(
            event_type="ACCESS_EXPIRY_SCHEDULED", entity_type="access_grant",
            entity_id=grant.id, organisation_id=req.organisation_id, request_id=req.id,
            new_state="EXPIRING", payload={"reason": "expiry reached"},
            request_id_header=self.request_id_header,
        )

    def attempt_revocation(self, grant: AccessGrant, *, force_outcome: str | None = None) -> RevocationAttempt:
        """Run one revocation attempt. Successful revocation is terminal."""
        # TODO: record a new RevocationAttempt; call self.provisioner.revoke(...);
        # on success, mark the grant/request REVOKED, audit + notify; on
        # failure, schedule a retry using self.retry_delays (request moves to
        # REVOCATION_FAILED) or, once retries are exhausted, escalate the
        # grant/request to ESCALATED as a compliance incident.
        raise NotImplementedError

    # ---- lookups ----

    def get_grant(self, grant_id: str) -> AccessGrant:
        grant = self.db.get(AccessGrant, grant_id)
        if not grant:
            raise NotFoundError("Access grant not found.")
        return grant
