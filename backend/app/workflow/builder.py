"""Build an approval workflow from a policy decision.

Groups required approvals by stage, creates one ApprovalStage per distinct stage
number, and one ApprovalTask per required role in that stage. A stage with more
than one approver runs in PARALLEL with minimum_approvals equal to the number of
tasks; a single-approver stage runs SEQUENTIAL. Deadlines come from the SLA
table (compressed for emergency requests).
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.enums import (
    ApprovalTaskStatus,
    ExecutionMode,
    StageStatus,
    WorkflowStatus,
)
from app.models.org import Resource, User
from app.models.request import ApprovalStage, ApprovalTask, ApprovalWorkflow
from app.policy_engine.types import PolicyDecision
from app.workflow.resolver import resolve_approver
from app.workflow.sla import sla_hours_for


def build_workflow(
    db: Session,
    *,
    request_id: str,
    decision: PolicyDecision,
    organisation_id: str,
    requester: User,
    resource: Resource | None,
    emergency: bool = False,
) -> ApprovalWorkflow:
    # TODO: create the ApprovalWorkflow; group decision.required_approval_stages
    # by stage number into one ApprovalStage each (PARALLEL with
    # minimum_approvals = role count if >1 role, else SEQUENTIAL), open only
    # the first stage, set each stage's deadline from the max SLA among its
    # roles (via sla_hours_for, compressed if `emergency`), and create one
    # ApprovalTask per role (resolved via resolve_approver), assigning/dating
    # only the tasks in the first (open) stage.
    raise NotImplementedError
