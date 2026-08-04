"""SLA escalation and notification delivery tasks (Milestones 4 tail + 6).

escalate_overdue_approvals: marks overdue pending tasks, notifies the approver,
escalates once (idempotent via a per-task escalated flag), and audits it.

send_notifications: delivers PENDING/RETRYING notifications through the mock
provider with bounded retry.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.core.logging import get_logger
from app.db.base import utcnow
from app.models.enums import ApprovalTaskStatus, StageStatus
from app.models.request import ApprovalStage, ApprovalTask, ApprovalWorkflow, Request
from app.notifications.service import NotificationService

log = get_logger("worker.sla")


def escalate_overdue_approvals(db: Session) -> None:
    now = utcnow()
    overdue = db.execute(
        select(ApprovalTask).where(
            ApprovalTask.status == ApprovalTaskStatus.PENDING,
            ApprovalTask.due_at.isnot(None),
            ApprovalTask.due_at <= now,
            ApprovalTask.escalated.is_(False),
        )
    ).scalars().all()

    audit = AuditService(db)
    notifications = NotificationService(db)

    for task in overdue:
        stage = db.get(ApprovalStage, task.approval_stage_id)
        if not stage or stage.status != StageStatus.IN_PROGRESS:
            continue
        workflow = db.get(ApprovalWorkflow, stage.workflow_id)
        req = db.get(Request, workflow.request_id)

        task.escalated = True
        task.lock_version += 1

        audit.record(
            event_type="SLA_ESCALATED", entity_type="approval_task", entity_id=task.id,
            organisation_id=req.organisation_id, request_id=req.id,
            payload={"role": task.approver_role, "stage": stage.stage_number,
                     "due_at": task.due_at.isoformat() if task.due_at else None},
        )
        # Notify the current approver (dedupe so we escalate-notify once).
        if task.approver_user_id:
            notifications.enqueue(
                user_id=task.approver_user_id, notification_type="APPROVAL_OVERDUE",
                subject=f"Overdue approval: '{req.title}'",
                dedupe_key=f"APPROVAL_OVERDUE:{task.id}",
            )
        log.info("sla_escalated", task_id=task.id, request_id=req.id)


def send_notifications(db: Session) -> None:
    NotificationService(db).deliver_pending()


def register(runner_register) -> None:
    runner_register("escalate_overdue_approvals")(escalate_overdue_approvals)
    runner_register("send_notifications")(send_notifications)
