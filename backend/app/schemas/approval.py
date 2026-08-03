from datetime import datetime

from pydantic import BaseModel


class DecisionIn(BaseModel):
    operation_id: str
    decision: str  # APPROVE | REJECT | REQUEST_CHANGES
    comment: str | None = None
    expected_version: int | None = None


class DelegateIn(BaseModel):
    to_user_id: str
    comment: str | None = None


class ReassignIn(BaseModel):
    to_user_id: str


class InboxItem(BaseModel):
    task_id: str
    request_id: str
    request_title: str
    request_type: str
    risk_level: str | None
    risk_score: int
    approver_role: str | None
    task_status: str
    stage_number: int
    due_at: datetime | None
    requester_id: str
    lock_version: int


class ApprovalTaskDetail(BaseModel):
    id: str
    approver_user_id: str | None
    approver_role: str | None
    status: str
    decision: str | None
    comment: str | None
    due_at: datetime | None
    acted_at: datetime | None
    lock_version: int

    class Config:
        from_attributes = True
