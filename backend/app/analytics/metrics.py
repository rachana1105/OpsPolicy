"""Compliance metrics computation.

In a real deployment these are Gold Delta tables refreshed by Databricks. Locally
the same metrics are computed directly from the operational DB so the compliance
dashboard is populated without a live Databricks account. The shape of the output
matches what the Databricks gold tables publish.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.enums import ApprovalTaskStatus, RequestStatus, RevocationStatus
from app.models.lifecycle import AccessGrant, PolicyException, RevocationAttempt
from app.models.org import User
from app.models.request import ApprovalStage, ApprovalTask, ApprovalWorkflow, Request


def compute_compliance_summary(db: Session, organisation_id: str) -> dict:
    requests = db.execute(
        select(Request).where(Request.organisation_id == organisation_id)
    ).scalars().all()
    total = len(requests)
    approved = [r for r in requests if r.status in (
        RequestStatus.APPROVED, RequestStatus.ACTIVE, RequestStatus.EXPIRING,
        RequestStatus.REVOKED, RequestStatus.PROVISIONING)]
    rejected = [r for r in requests if r.status == RequestStatus.REJECTED]

    # Approval durations (submitted -> approved).
    durations = []
    for r in requests:
        if r.submitted_at and r.approved_at:
            durations.append((r.approved_at - r.submitted_at).total_seconds() / 3600.0)
    durations.sort()

    def pct(p):
        if not durations:
            return 0.0
        idx = min(len(durations) - 1, int(p / 100 * len(durations)))
        return round(durations[idx], 2)

    avg = round(sum(durations) / len(durations), 2) if durations else 0.0

    by_risk = Counter(r.risk_level.value for r in requests if r.risk_level)
    by_type = Counter(r.request_type.value for r in requests)

    return {
        "total_requests": total,
        "approved": len(approved),
        "rejected": len(rejected),
        "approval_rate": round(len(approved) / total, 3) if total else 0.0,
        "rejection_rate": round(len(rejected) / total, 3) if total else 0.0,
        "avg_approval_hours": avg,
        "p95_approval_hours": pct(95),
        "risk_distribution": dict(by_risk),
        "requests_by_type": dict(by_type),
        "generated_at": utcnow().isoformat(),
    }


def compute_approval_sla(db: Session, organisation_id: str) -> dict:
    now = utcnow()
    tasks = db.execute(
        select(ApprovalTask)
        .join(ApprovalStage, ApprovalTask.approval_stage_id == ApprovalStage.id)
        .join(ApprovalWorkflow, ApprovalStage.workflow_id == ApprovalWorkflow.id)
        .join(Request, ApprovalWorkflow.request_id == Request.id)
        .where(Request.organisation_id == organisation_id)
    ).scalars().all()
    total = len(tasks)
    breached = sum(1 for t in tasks if t.due_at and (
        (t.acted_at and t.acted_at > t.due_at) or
        (not t.acted_at and t.due_at < now and t.status == ApprovalTaskStatus.PENDING)))
    by_role = defaultdict(lambda: {"count": 0, "hours": 0.0})
    for t in tasks:
        if t.assigned_at and t.acted_at:
            r = by_role[t.approver_role or "UNKNOWN"]
            r["count"] += 1
            r["hours"] += (t.acted_at - t.assigned_at).total_seconds() / 3600.0
    avg_by_role = {role: round(v["hours"] / v["count"], 2)
                   for role, v in by_role.items() if v["count"]}
    return {
        "total_tasks": total,
        "breached": breached,
        "sla_compliance": round((total - breached) / total, 3) if total else 1.0,
        "avg_hours_by_role": avg_by_role,
        "generated_at": now.isoformat(),
    }


def compute_department_risk(db: Session, organisation_id: str) -> dict:
    requests = db.execute(
        select(Request).where(Request.organisation_id == organisation_id)
    ).scalars().all()
    users = {u.id: u for u in db.execute(
        select(User).where(User.organisation_id == organisation_id)).scalars().all()}
    by_team = defaultdict(lambda: {"count": 0, "high_risk": 0, "total_score": 0})
    for r in requests:
        u = users.get(r.requester_id)
        team = (u.team_id if u else None) or "unassigned"
        b = by_team[team]
        b["count"] += 1
        b["total_score"] += r.risk_score
        if r.risk_level and r.risk_level.value in ("HIGH", "CRITICAL"):
            b["high_risk"] += 1
    return {
        "by_team": {k: {**v, "avg_score": round(v["total_score"] / v["count"], 1)}
                    for k, v in by_team.items() if v["count"]},
        "generated_at": utcnow().isoformat(),
    }


def compute_revocation_failures(db: Session, organisation_id: str) -> dict:
    grants = db.execute(
        select(AccessGrant)
        .join(Request, AccessGrant.request_id == Request.id)
        .where(Request.organisation_id == organisation_id)
    ).scalars().all()
    failed = [g for g in grants if g.revocation_status in (
        RevocationStatus.FAILED, RevocationStatus.ESCALATED)]
    escalated = [g for g in grants if g.revocation_status == RevocationStatus.ESCALATED]
    attempts = db.execute(select(RevocationAttempt)).scalars().all()
    grant_ids = {g.id for g in grants}
    total_attempts = sum(1 for a in attempts if a.access_grant_id in grant_ids)
    return {
        "failed_revocations": len(failed),
        "escalated": len(escalated),
        "total_attempts": total_attempts,
        "generated_at": utcnow().isoformat(),
    }


def compute_exception_trends(db: Session, organisation_id: str) -> dict:
    exceptions = db.execute(
        select(PolicyException)
        .join(Request, PolicyException.request_id == Request.id)
        .where(Request.organisation_id == organisation_id)
    ).scalars().all()
    by_status = Counter(e.status.value for e in exceptions)
    return {
        "total": len(exceptions),
        "by_status": dict(by_status),
        "generated_at": utcnow().isoformat(),
    }
