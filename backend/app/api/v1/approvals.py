from fastapi import APIRouter, Depends, Query, Request as FastAPIRequest
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.org import User
from app.schemas.approval import (
    ApprovalTaskDetail,
    DecisionIn,
    DelegateIn,
    InboxItem,
    ReassignIn,
)
from app.services.approval_service import ApprovalService

router = APIRouter(prefix="/approvals", tags=["approvals"])


def _svc(req: FastAPIRequest, db: Session) -> ApprovalService:
    return ApprovalService(db, request_id_header=getattr(req.state, "request_id", None))


@router.get("/inbox", response_model=list[InboxItem])
def inbox(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    include_done: bool = Query(False),
):
    svc = ApprovalService(db)
    rows = svc.inbox(user, only_pending=not include_done)
    items: list[InboxItem] = []
    for row in rows:
        task, stage, req = row["task"], row["stage"], row["request"]
        items.append(InboxItem(
            task_id=task.id, request_id=req.id, request_title=req.title,
            request_type=req.request_type.value,
            risk_level=req.risk_level.value if req.risk_level else None,
            risk_score=req.risk_score, approver_role=task.approver_role,
            task_status=task.status.value, stage_number=stage.stage_number,
            due_at=task.due_at, requester_id=req.requester_id,
            lock_version=task.lock_version,
        ))
    # Sort: overdue/urgent first by due date, then by risk.
    items.sort(key=lambda i: (i.due_at is None, i.due_at or "", -i.risk_score))
    return items


@router.get("/{task_id}", response_model=ApprovalTaskDetail)
def get_task(task_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = ApprovalService(db)
    task = svc.get_task(task_id)
    return ApprovalTaskDetail.model_validate(task)


@router.post("/{task_id}/decision", response_model=ApprovalTaskDetail)
def decide(
    task_id: str, body: DecisionIn, req: FastAPIRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    svc = _svc(req, db)
    task = svc.get_task(task_id)
    result = svc.decide(
        task=task, actor=user, operation_id=body.operation_id,
        decision=body.decision, comment=body.comment,
        expected_version=body.expected_version,
    )
    db.commit()
    db.refresh(result)
    return ApprovalTaskDetail.model_validate(result)


@router.post("/{task_id}/delegate", response_model=ApprovalTaskDetail)
def delegate(
    task_id: str, body: DelegateIn, req: FastAPIRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    svc = _svc(req, db)
    task = svc.get_task(task_id)
    result = svc.delegate(task=task, actor=user, to_user_id=body.to_user_id, comment=body.comment)
    db.commit()
    db.refresh(result)
    return ApprovalTaskDetail.model_validate(result)


@router.post("/{task_id}/reassign", response_model=ApprovalTaskDetail)
def reassign(
    task_id: str, body: ReassignIn, req: FastAPIRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    svc = _svc(req, db)
    task = svc.get_task(task_id)
    result = svc.reassign(task=task, actor=user, to_user_id=body.to_user_id)
    db.commit()
    db.refresh(result)
    return ApprovalTaskDetail.model_validate(result)
