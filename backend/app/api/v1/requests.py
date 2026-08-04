from datetime import datetime

from fastapi import APIRouter, Depends, Query, Request as FastAPIRequest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import ForbiddenError, NotFoundError
from app.db.session import get_db
from app.models.enums import RequestStatus, RequestType, RiskLevel
from app.models.org import User
from app.models.request import (
    ApprovalStage,
    ApprovalTask,
    ApprovalWorkflow,
    Request,
)
from app.schemas.request import (
    ApprovalStageOut,
    ApprovalTaskOut,
    RequestCreate,
    RequestOut,
    RequestUpdate,
    TimelineEvent,
    WorkflowOut,
)
from app.services.request_service import RequestService
from app.provisioning.lifecycle import AccessLifecycleService
from app.audit.service import AuditService

router = APIRouter(prefix="/requests", tags=["requests"])


def _svc(req: FastAPIRequest, db: Session) -> RequestService:
    return RequestService(db, request_id_header=getattr(req.state, "request_id", None))


def _get_owned_or_visible(db: Session, request_id: str, user: User) -> Request:
    r = db.get(Request, request_id)
    if not r or r.organisation_id != user.organisation_id:
        raise NotFoundError("Request not found.")
    return r


@router.post("", response_model=RequestOut, status_code=201)
def create_request(
    body: RequestCreate,
    req: FastAPIRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = _svc(req, db)
    r = service.create_draft(
        requester=user, request_type=body.request_type, title=body.title,
        resource_id=body.resource_id, business_justification=body.business_justification,
        payload=body.payload,
    )
    db.commit()
    db.refresh(r)
    return RequestOut.model_validate(_serialise(r))


@router.get("", response_model=list[RequestOut])
def list_requests(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request_type: RequestType | None = None,
    status: RequestStatus | None = None,
    risk_level: RiskLevel | None = None,
    requester_id: str | None = None,
    resource_id: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    mine: bool = Query(False, description="Only requests I submitted"),
):
    stmt = select(Request).where(Request.organisation_id == user.organisation_id)
    if mine:
        stmt = stmt.where(Request.requester_id == user.id)
    if request_type:
        stmt = stmt.where(Request.request_type == request_type)
    if status:
        stmt = stmt.where(Request.status == status)
    if risk_level:
        stmt = stmt.where(Request.risk_level == risk_level)
    if requester_id:
        stmt = stmt.where(Request.requester_id == requester_id)
    if resource_id:
        stmt = stmt.where(Request.resource_id == resource_id)
    if created_from:
        stmt = stmt.where(Request.created_at >= created_from)
    if created_to:
        stmt = stmt.where(Request.created_at <= created_to)
    stmt = stmt.order_by(Request.created_at.desc())
    return [RequestOut.model_validate(_serialise(r)) for r in db.execute(stmt).scalars().all()]


@router.get("/{request_id}", response_model=RequestOut)
def get_request(request_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = _get_owned_or_visible(db, request_id, user)
    return RequestOut.model_validate(_serialise(r))


@router.put("/{request_id}", response_model=RequestOut)
def update_request(
    request_id: str, body: RequestUpdate,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    r = _get_owned_or_visible(db, request_id, user)
    if r.requester_id != user.id:
        raise ForbiddenError("Only the requester can edit this request.")
    if r.status != RequestStatus.DRAFT:
        raise ForbiddenError("Only draft requests can be edited.")
    if body.title is not None:
        r.title = body.title
    if body.business_justification is not None:
        r.business_justification = body.business_justification
    if body.payload is not None:
        r.request_payload = body.payload
    db.commit()
    db.refresh(r)
    return RequestOut.model_validate(_serialise(r))


@router.post("/{request_id}/submit", response_model=RequestOut)
def submit_request(
    request_id: str, req: FastAPIRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    r = _get_owned_or_visible(db, request_id, user)
    service = _svc(req, db)
    service.submit(req=r, actor=user)
    db.commit()
    db.refresh(r)
    return RequestOut.model_validate(_serialise(r))


@router.post("/{request_id}/cancel", response_model=RequestOut)
def cancel_request(
    request_id: str, req: FastAPIRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    r = _get_owned_or_visible(db, request_id, user)
    service = _svc(req, db)
    service.cancel(req=r, actor=user)
    db.commit()
    db.refresh(r)
    return RequestOut.model_validate(_serialise(r))


@router.post("/{request_id}/provision", response_model=RequestOut)
def provision_request(
    request_id: str, req: FastAPIRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    """Provision an approved request immediately (also runs automatically via the
    worker). Available to the requester or an approver in the same org."""
    r = _get_owned_or_visible(db, request_id, user)
    svc = AccessLifecycleService(db, request_id_header=getattr(req.state, "request_id", None))
    svc.provision_request(r)
    db.commit()
    db.refresh(r)
    return RequestOut.model_validate(_serialise(r))


@router.get("/{request_id}/timeline", response_model=list[TimelineEvent])
def request_timeline(request_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_owned_or_visible(db, request_id, user)
    events = AuditService(db).timeline(request_id)
    return [TimelineEvent.model_validate(e) for e in events]


@router.get("/{request_id}/workflow", response_model=WorkflowOut | None)
def request_workflow(request_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    _get_owned_or_visible(db, request_id, user)
    wf = db.execute(
        select(ApprovalWorkflow).where(ApprovalWorkflow.request_id == request_id)
    ).scalar_one_or_none()
    if not wf:
        return None
    stages = db.execute(
        select(ApprovalStage).where(ApprovalStage.workflow_id == wf.id)
        .order_by(ApprovalStage.stage_number)
    ).scalars().all()
    out_stages = []
    for s in stages:
        tasks = db.execute(
            select(ApprovalTask).where(ApprovalTask.approval_stage_id == s.id)
        ).scalars().all()
        out_stages.append(ApprovalStageOut(
            id=s.id, stage_number=s.stage_number, execution_mode=s.execution_mode.value,
            minimum_approvals=s.minimum_approvals, status=s.status.value,
            deadline_at=s.deadline_at,
            tasks=[ApprovalTaskOut(
                id=t.id, approver_user_id=t.approver_user_id, approver_role=t.approver_role,
                status=t.status.value, decision=t.decision, comment=t.comment,
                due_at=t.due_at, acted_at=t.acted_at,
            ) for t in tasks],
        ))
    return WorkflowOut(id=wf.id, status=wf.status.value, current_stage=wf.current_stage, stages=out_stages)


def _serialise(r: Request) -> dict:
    return {
        "id": r.id, "request_type": r.request_type.value, "requester_id": r.requester_id,
        "resource_id": r.resource_id, "title": r.title,
        "business_justification": r.business_justification, "request_payload": r.request_payload,
        "risk_score": r.risk_score, "risk_level": r.risk_level.value if r.risk_level else None,
        "decision": r.decision.value if r.decision else None, "status": r.status.value,
        "submitted_at": r.submitted_at, "approved_at": r.approved_at,
        "expires_at": r.expires_at, "created_at": r.created_at,
    }
