from datetime import datetime

from fastapi import APIRouter, Depends, Request as FastAPIRequest
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.org import User
from app.services.exception_service import ExceptionService

router = APIRouter(prefix="/exceptions", tags=["exceptions"])


def _svc(req: FastAPIRequest, db: Session) -> ExceptionService:
    return ExceptionService(db, request_id_header=getattr(req.state, "request_id", None))


class ExceptionCreate(BaseModel):
    request_id: str
    policy_id: str | None = None
    justification: str
    risk_description: str | None = None
    compensating_controls: str | None = None
    start_at: datetime
    expires_at: datetime


class RejectBody(BaseModel):
    reason: str | None = None


class ExceptionOut(BaseModel):
    id: str
    request_id: str
    policy_id: str | None
    requested_by: str
    justification: str
    risk_description: str | None
    compensating_controls: str | None
    start_at: datetime
    expires_at: datetime
    status: str
    approved_at: datetime | None
    approved_by: str | None
    revoked_at: datetime | None

    class Config:
        from_attributes = True


@router.post("", response_model=ExceptionOut, status_code=201)
def create_exception(
    body: ExceptionCreate, req: FastAPIRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    exc = _svc(req, db).request_exception(
        request_id=body.request_id, actor=user, policy_id=body.policy_id,
        justification=body.justification, risk_description=body.risk_description,
        compensating_controls=body.compensating_controls,
        start_at=body.start_at, expires_at=body.expires_at,
    )
    db.commit()
    db.refresh(exc)
    return ExceptionOut.model_validate(exc)


@router.get("", response_model=list[ExceptionOut])
def list_exceptions(
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
    status: str | None = None,
):
    exceptions = ExceptionService(db).list_for_org(user.organisation_id, status=status)
    return [ExceptionOut.model_validate(e) for e in exceptions]


@router.post("/{exception_id}/approve", response_model=ExceptionOut)
def approve_exception(
    exception_id: str, req: FastAPIRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    exc = _svc(req, db).approve(exception_id=exception_id, actor=user)
    db.commit()
    db.refresh(exc)
    return ExceptionOut.model_validate(exc)


@router.post("/{exception_id}/reject", response_model=ExceptionOut)
def reject_exception(
    exception_id: str, body: RejectBody, req: FastAPIRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    exc = _svc(req, db).reject(exception_id=exception_id, actor=user, reason=body.reason)
    db.commit()
    db.refresh(exc)
    return ExceptionOut.model_validate(exc)


@router.post("/{exception_id}/revoke", response_model=ExceptionOut)
def revoke_exception(
    exception_id: str, req: FastAPIRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    exc = _svc(req, db).revoke(exception_id=exception_id, actor=user)
    db.commit()
    db.refresh(exc)
    return ExceptionOut.model_validate(exc)
