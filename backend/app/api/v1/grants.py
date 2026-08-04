from fastapi import APIRouter, Depends, Query, Request as FastAPIRequest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_roles
from app.core.errors import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.models.enums import ProvisioningStatus, RevocationStatus, Role
from app.models.lifecycle import AccessGrant, RevocationAttempt
from app.models.org import User
from app.models.request import Request
from app.provisioning.lifecycle import AccessLifecycleService
from app.schemas.grant import AccessGrantOut, RevocationAttemptOut

router = APIRouter(prefix="/access-grants", tags=["access-grants"])


def _visible(db: Session, grant_id: str, user: User) -> AccessGrant:
    grant = db.get(AccessGrant, grant_id)
    if not grant:
        raise NotFoundError("Access grant not found.")
    req = db.get(Request, grant.request_id)
    if not req or req.organisation_id != user.organisation_id:
        raise NotFoundError("Access grant not found.")
    return grant


@router.get("", response_model=list[AccessGrantOut])
def list_grants(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    mine: bool = Query(False),
    active_only: bool = Query(False),
):
    # Join to requests to scope by organisation.
    stmt = (
        select(AccessGrant)
        .join(Request, AccessGrant.request_id == Request.id)
        .where(Request.organisation_id == user.organisation_id)
    )
    if mine:
        stmt = stmt.where(AccessGrant.user_id == user.id)
    if active_only:
        stmt = stmt.where(
            AccessGrant.provisioning_status == ProvisioningStatus.SUCCEEDED,
            AccessGrant.revocation_status == RevocationStatus.PENDING,
        )
    stmt = stmt.order_by(AccessGrant.created_at.desc())
    return [AccessGrantOut.model_validate(g) for g in db.execute(stmt).scalars().all()]


@router.get("/{grant_id}", response_model=AccessGrantOut)
def get_grant(grant_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return AccessGrantOut.model_validate(_visible(db, grant_id, user))


@router.get("/{grant_id}/revocation-attempts", response_model=list[RevocationAttemptOut])
def revocation_attempts(grant_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _visible(db, grant_id, user)
    attempts = db.execute(
        select(RevocationAttempt)
        .where(RevocationAttempt.access_grant_id == grant_id)
        .order_by(RevocationAttempt.attempt_number)
    ).scalars().all()
    return [RevocationAttemptOut.model_validate(a) for a in attempts]


@router.post("/{grant_id}/revoke", response_model=AccessGrantOut)
def revoke_grant(
    grant_id: str, req: FastAPIRequest,
    user: User = Depends(require_roles(Role.PLATFORM_ADMIN.value, Role.COMPLIANCE_OFFICER.value)),
    db: Session = Depends(get_db),
):
    grant = _visible(db, grant_id, user)
    svc = AccessLifecycleService(db, request_id_header=getattr(req.state, "request_id", None))
    # Manual revoke: mark expiring if still active, then attempt.
    if grant.revocation_status == RevocationStatus.PENDING:
        svc.mark_expiring(grant)
    svc.attempt_revocation(grant)
    db.commit()
    db.refresh(grant)
    return AccessGrantOut.model_validate(grant)
