from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.audit.service import AuditService
from app.db.session import get_db
from app.models.org import User

router = APIRouter(prefix="/audit", tags=["audit"])


class AuditEventOut(BaseModel):
    id: str
    request_id: str | None
    actor_id: str | None
    event_type: str
    entity_type: str
    entity_id: str | None
    previous_state: str | None
    new_state: str | None
    payload: dict
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("/events", response_model=list[AuditEventOut])
def search_events(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    request_id: str | None = None,
    actor_id: str | None = None,
    event_type: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    created_from: datetime | None = None,
    created_to: datetime | None = None,
):
    events = AuditService(db).search(
        organisation_id=user.organisation_id, request_id=request_id, actor_id=actor_id,
        event_type=event_type, entity_type=entity_type, entity_id=entity_id,
        created_from=created_from, created_to=created_to,
    )
    return [AuditEventOut.model_validate(e) for e in events]


@router.get("/event-types", response_model=list[str])
def event_types(user: User = Depends(get_current_user)):
    return sorted([
        "REQUEST_CREATED", "REQUEST_SUBMITTED", "POLICY_EVALUATED", "RISK_CALCULATED",
        "WORKFLOW_CREATED", "APPROVAL_ASSIGNED", "APPROVAL_GRANTED", "APPROVAL_REJECTED",
        "APPROVAL_CHANGES_REQUESTED", "APPROVAL_DELEGATED", "SLA_ESCALATED",
        "REQUEST_APPROVED", "REQUEST_REJECTED", "REQUEST_CANCELLED",
        "ACCESS_PROVISIONED", "ACCESS_EXPIRY_SCHEDULED", "REVOCATION_ATTEMPTED",
        "ACCESS_REVOKED", "REVOCATION_FAILED",
    ])
