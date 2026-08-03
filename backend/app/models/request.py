"""Requests, policy evaluations, and approval workflow models."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import UTCDateTime
from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import (
    ApprovalTaskStatus,
    Decision,
    ExecutionMode,
    RequestStatus,
    RequestType,
    RiskLevel,
    StageStatus,
    WorkflowStatus,
)


class Request(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "requests"
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), nullable=False)
    request_type: Mapped[RequestType] = mapped_column(nullable=False)
    requester_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(ForeignKey("resources.id"), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    business_justification: Mapped[str | None] = mapped_column(Text, nullable=True)
    request_payload: Mapped[dict] = mapped_column(JSON, default=dict)
    risk_score: Mapped[int] = mapped_column(Integer, default=0)
    risk_level: Mapped[RiskLevel | None] = mapped_column(nullable=True)
    decision: Mapped[Decision | None] = mapped_column(nullable=True)
    status: Mapped[RequestStatus] = mapped_column(default=RequestStatus.DRAFT, nullable=False)
    # optimistic-lock version
    lock_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class PolicyEvaluation(Base, UUIDMixin):
    __tablename__ = "policy_evaluations"
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), nullable=False)
    policy_id: Mapped[str] = mapped_column(String(36), nullable=False)
    policy_version_id: Mapped[str] = mapped_column(String(36), nullable=False)
    matched: Mapped[bool] = mapped_column(default=False)
    result: Mapped[dict] = mapped_column(JSON, default=dict)
    violations: Mapped[list] = mapped_column(JSON, default=list)
    required_actions: Mapped[list] = mapped_column(JSON, default=list)
    risk_contribution: Mapped[int] = mapped_column(Integer, default=0)
    evaluated_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)


class ApprovalWorkflow(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "approval_workflows"
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), nullable=False)
    status: Mapped[WorkflowStatus] = mapped_column(default=WorkflowStatus.PENDING, nullable=False)
    current_stage: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    lock_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ApprovalStage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "approval_stages"
    workflow_id: Mapped[str] = mapped_column(ForeignKey("approval_workflows.id"), nullable=False)
    stage_number: Mapped[int] = mapped_column(Integer, nullable=False)
    execution_mode: Mapped[ExecutionMode] = mapped_column(default=ExecutionMode.SEQUENTIAL)
    minimum_approvals: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[StageStatus] = mapped_column(default=StageStatus.PENDING, nullable=False)
    deadline_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class ApprovalTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "approval_tasks"
    approval_stage_id: Mapped[str] = mapped_column(ForeignKey("approval_stages.id"), nullable=False)
    approver_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approver_role: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[ApprovalTaskStatus] = mapped_column(default=ApprovalTaskStatus.PENDING, nullable=False)
    decision: Mapped[str | None] = mapped_column(String(32), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    acted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    due_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    delegated_from_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    escalated: Mapped[bool] = mapped_column(default=False)
    lock_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # idempotency: last operation_id applied
    last_operation_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
