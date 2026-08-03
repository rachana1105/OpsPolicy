from datetime import datetime

from pydantic import BaseModel

from app.models.enums import RequestType


class RequestCreate(BaseModel):
    request_type: RequestType
    title: str
    resource_id: str | None = None
    business_justification: str | None = None
    payload: dict = {}


class RequestUpdate(BaseModel):
    title: str | None = None
    business_justification: str | None = None
    payload: dict | None = None


class RequestOut(BaseModel):
    id: str
    request_type: str
    requester_id: str
    resource_id: str | None
    title: str
    business_justification: str | None
    request_payload: dict
    risk_score: int
    risk_level: str | None
    decision: str | None
    status: str
    submitted_at: datetime | None
    approved_at: datetime | None
    expires_at: datetime | None
    created_at: datetime

    class Config:
        from_attributes = True


class TimelineEvent(BaseModel):
    id: str
    event_type: str
    entity_type: str
    actor_id: str | None
    previous_state: str | None
    new_state: str | None
    payload: dict
    created_at: datetime

    class Config:
        from_attributes = True


class ApprovalTaskOut(BaseModel):
    id: str
    approver_user_id: str | None
    approver_role: str | None
    status: str
    decision: str | None
    comment: str | None
    due_at: datetime | None
    acted_at: datetime | None

    class Config:
        from_attributes = True


class ApprovalStageOut(BaseModel):
    id: str
    stage_number: int
    execution_mode: str
    minimum_approvals: int
    status: str
    deadline_at: datetime | None
    tasks: list[ApprovalTaskOut]


class WorkflowOut(BaseModel):
    id: str
    status: str
    current_stage: int
    stages: list[ApprovalStageOut]
