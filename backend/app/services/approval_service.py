"""Approval decision engine (Milestone 4).

Handles an approver acting on a task: approve, reject, or request changes, plus
delegation and reassignment. The design enforces the spec's safety rules:

  * Idempotent actions — a repeated operation_id returns the same result without
    creating a duplicate transition.
  * Optimistic locking — task and workflow carry lock_version; a stale write is
    rejected so two approvers racing on the same task commit only one transition.
  * Conflict-of-interest — the requester can never approve their own request, and
    an approver only acts on a task assigned to them (or unassigned, for their
    role).
  * No action after completion — approving a cancelled/closed task or a finished
    workflow is refused.
  * Stage advancement — when a stage reaches its minimum approvals it completes
    and the next stage opens (its tasks become assigned with due dates); when the
    final stage completes the request moves to APPROVED. Any rejection rejects the
    workflow and the request.
"""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.db.base import utcnow
from app.models.enums import (
    ApprovalTaskStatus,
    RequestStatus,
    Role,
    StageStatus,
    WorkflowStatus,
)
from app.models.org import User
from app.models.request import (
    ApprovalStage,
    ApprovalTask,
    ApprovalWorkflow,
    Request,
)
from app.workflow.sla import sla_hours_for
from app.workflow.transitions import assert_transition
from app.notifications.service import NotificationService

TERMINAL_TASK = {
    ApprovalTaskStatus.APPROVED,
    ApprovalTaskStatus.REJECTED,
    ApprovalTaskStatus.CHANGES_REQUESTED,
    ApprovalTaskStatus.CANCELLED,
    ApprovalTaskStatus.EXPIRED,
}


class ApprovalService:
    def __init__(self, db: Session, request_id_header: str | None = None):
        self.db = db
        self.audit = AuditService(db)
        self.notifications = NotificationService(db)
        self.request_id_header = request_id_header

    # ---- lookups ----

    def get_task(self, task_id: str) -> ApprovalTask:
        task = self.db.get(ApprovalTask, task_id)
        if not task:
            raise NotFoundError("Approval task not found.")
        return task

    def _stage(self, task: ApprovalTask) -> ApprovalStage:
        return self.db.get(ApprovalStage, task.approval_stage_id)

    def _workflow(self, stage: ApprovalStage) -> ApprovalWorkflow:
        return self.db.get(ApprovalWorkflow, stage.workflow_id)

    def _request(self, workflow: ApprovalWorkflow) -> Request:
        return self.db.get(Request, workflow.request_id)

    def inbox(self, user: User, *, only_pending: bool = True) -> list[dict]:
        """Tasks assigned to this user (or unassigned tasks for their role)."""
        stmt = select(ApprovalTask).where(
            (ApprovalTask.approver_user_id == user.id)
            | (
                (ApprovalTask.approver_user_id.is_(None))
                & (ApprovalTask.approver_role == user.role.value)
            )
        )
        if only_pending:
            stmt = stmt.where(ApprovalTask.status == ApprovalTaskStatus.PENDING)
        tasks = self.db.execute(stmt).scalars().all()

        rows: list[dict] = []
        for task in tasks:
            stage = self._stage(task)
            workflow = self._workflow(stage)
            req = self._request(workflow)
            if req.organisation_id != user.organisation_id:
                continue
            # Only surface tasks whose stage is actually open.
            if only_pending and stage.status != StageStatus.IN_PROGRESS:
                continue
            rows.append({"task": task, "stage": stage, "request": req})
        return rows

    # ---- decision ----

    def decide(
        self,
        *,
        task: ApprovalTask,
        actor: User,
        operation_id: str,
        decision: str,  # APPROVE | REJECT | REQUEST_CHANGES
        comment: str | None,
        expected_version: int | None = None,
    ) -> ApprovalTask:
        # TODO: idempotency check on operation_id; optimistic-lock check
        # against expected_version; guard rails (workflow/stage open, task
        # not terminal, requester can't approve own request, task assigned
        # to this actor or role); then apply APPROVE (-> _maybe_advance),
        # REJECT (-> _reject_workflow), or REQUEST_CHANGES
        # (-> _request_changes), auditing each decision.
        raise NotImplementedError

    # ---- stage advancement ----

    def _maybe_advance(self, req: Request, workflow: ApprovalWorkflow,
                       stage: ApprovalStage, actor: User) -> None:
        # TODO: check whether the current stage has reached its
        # minimum_approvals; if not, mark the request PARTIALLY_APPROVED
        # when the stage needs multiple approvals. If met, complete the
        # stage, cancel remaining pending tasks in it, and either advance to
        # the next PENDING stage (assigning its tasks with SLA due dates and
        # notifying approvers) or, if no stages remain, complete the
        # workflow and mark the request APPROVED.
        raise NotImplementedError
        workflow.status = WorkflowStatus.REJECTED
        workflow.lock_version += 1
        # Cancel remaining pending tasks.
        for t in self.db.execute(
            select(ApprovalTask)
            .join(ApprovalStage, ApprovalTask.approval_stage_id == ApprovalStage.id)
            .where(ApprovalStage.workflow_id == workflow.id,
                   ApprovalTask.status == ApprovalTaskStatus.PENDING)
        ).scalars().all():
            t.status = ApprovalTaskStatus.CANCELLED
            t.lock_version += 1
        assert_transition(req.status, RequestStatus.REJECTED)
        req.status = RequestStatus.REJECTED
        req.completed_at = utcnow()
        req.lock_version += 1
        self._audit(req, "REQUEST_REJECTED", req.id, actor.id, {"auto": False})
        self.notifications.enqueue(
            user_id=req.requester_id, notification_type="REQUEST_REJECTED",
            subject=f"Your request '{req.title}' was rejected",
            dedupe_key=f"REQUEST_REJECTED:{req.id}",
        )

    def _request_changes(self, req: Request, workflow: ApprovalWorkflow, actor: User) -> None:
        # Send back to the requester; workflow is cancelled and a fresh submit
        # will re-evaluate and rebuild.
        workflow.status = WorkflowStatus.CANCELLED
        workflow.lock_version += 1
        for t in self.db.execute(
            select(ApprovalTask)
            .join(ApprovalStage, ApprovalTask.approval_stage_id == ApprovalStage.id)
            .where(ApprovalStage.workflow_id == workflow.id,
                   ApprovalTask.status == ApprovalTaskStatus.PENDING)
        ).scalars().all():
            t.status = ApprovalTaskStatus.CANCELLED
            t.lock_version += 1
        assert_transition(req.status, RequestStatus.CHANGES_REQUESTED)
        req.status = RequestStatus.CHANGES_REQUESTED
        req.lock_version += 1

    # ---- delegation / reassignment ----

    def delegate(self, *, task: ApprovalTask, actor: User, to_user_id: str,
                 comment: str | None = None) -> ApprovalTask:
        if task.status != ApprovalTaskStatus.PENDING:
            raise ConflictError("Only a pending task can be delegated.")
        if task.approver_user_id and task.approver_user_id != actor.id:
            raise ForbiddenError("You can only delegate your own task.")
        target = self.db.get(User, to_user_id)
        if not target or target.organisation_id != actor.organisation_id:
            raise NotFoundError("Delegate target not found.")
        req = self._request(self._workflow(self._stage(task)))
        if target.id == req.requester_id:
            raise ForbiddenError("Cannot delegate to the requester.")
        task.delegated_from_user_id = actor.id
        task.approver_user_id = target.id
        task.comment = comment
        task.lock_version += 1
        self._audit(req, "APPROVAL_DELEGATED", task.id, actor.id,
                    {"from": actor.id, "to": target.id})
        self.db.flush()
        return task

    def reassign(self, *, task: ApprovalTask, actor: User, to_user_id: str) -> ApprovalTask:
        # Reassignment is an admin/manager action; here we allow platform admins.
        if actor.role != Role.PLATFORM_ADMIN:
            raise ForbiddenError("Only a platform admin can reassign tasks.")
        target = self.db.get(User, to_user_id)
        if not target or target.organisation_id != actor.organisation_id:
            raise NotFoundError("Reassign target not found.")
        req = self._request(self._workflow(self._stage(task)))
        if target.id == req.requester_id:
            raise ForbiddenError("Cannot reassign to the requester.")
        task.approver_user_id = target.id
        task.lock_version += 1
        self._audit(req, "APPROVAL_ASSIGNED", task.id, actor.id,
                    {"reassigned_to": target.id})
        self.db.flush()
        return task

    # ---- helper ----

    def _audit(self, req: Request, event_type: str, entity_id: str,
               actor_id: str, payload: dict) -> None:
        self.audit.record(
            event_type=event_type, entity_type="approval_task", entity_id=entity_id,
            organisation_id=req.organisation_id, request_id=req.id, actor_id=actor_id,
            payload=payload, request_id_header=self.request_id_header,
        )
