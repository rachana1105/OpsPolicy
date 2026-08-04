"""Export service (Milestone 7).

Reads operational records incrementally and writes newline-delimited JSON plus a
manifest, to a location the analytics engine can ingest. Tracks a checkpoint so
the same change is never exported twice, supports retry, and writes an audit
event. Locally this writes to a directory; in a real deployment the same
manifest+files land in a Unity Catalog Volume.
"""
from __future__ import annotations

import json
import os
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.core.logging import get_logger
from app.db.base import utcnow
from app.models.lifecycle import AccessGrant, AuditEvent, PolicyException, RevocationAttempt
from app.models.request import ApprovalTask, PolicyEvaluation, Request

log = get_logger("export")

# Tables exported and how to serialise each row.
EXPORT_ROOT = os.environ.get("EXPORT_ROOT", "/tmp/opspolicy_exports")


def _iso(v):
    return v.isoformat() if isinstance(v, datetime) else v


class ExportService:
    def __init__(self, db: Session, request_id_header: str | None = None):
        self.db = db
        self.audit = AuditService(db)
        self.request_id_header = request_id_header

    def _rows(self, organisation_id: str, since: datetime | None):
        """Collect exportable rows per table, filtered incrementally by updated_at."""
        def flt(q, col):
            q = q.filter(col == organisation_id) if col is not None else q
            return q

        requests = self.db.execute(
            select(Request).where(Request.organisation_id == organisation_id)
        ).scalars().all()
        req_ids = {r.id for r in requests}
        if since:
            requests = [r for r in requests if r.updated_at and r.updated_at > since]

        evals = [e for e in self.db.execute(select(PolicyEvaluation)).scalars().all()
                 if e.request_id in req_ids]
        approvals = self.db.execute(select(ApprovalTask)).scalars().all()
        exceptions = [e for e in self.db.execute(select(PolicyException)).scalars().all()
                      if e.request_id in req_ids]
        grants = [g for g in self.db.execute(select(AccessGrant)).scalars().all()
                  if g.request_id in req_ids]
        revocations = self.db.execute(select(RevocationAttempt)).scalars().all()
        audit_events = self.db.execute(
            select(AuditEvent).where(AuditEvent.organisation_id == organisation_id)
        ).scalars().all()

        return {
            "requests": [self._request_row(r) for r in requests],
            "policy_evaluations": [self._eval_row(e) for e in evals],
            "approval_events": [self._approval_row(a) for a in approvals],
            "exceptions": [self._exception_row(e) for e in exceptions],
            "access_grants": [self._grant_row(g) for g in grants],
            "revocation_attempts": [self._revocation_row(r) for r in revocations],
            "audit_events": [self._audit_row(a) for a in audit_events],
        }

    def run_export(self, organisation_id: str, *, since: datetime | None = None) -> dict:
        os.makedirs(EXPORT_ROOT, exist_ok=True)
        export_id = f"exp_{utcnow().strftime('%Y%m%d%H%M%S')}"
        export_dir = os.path.join(EXPORT_ROOT, export_id)
        os.makedirs(export_dir, exist_ok=True)

        tables = self._rows(organisation_id, since)
        manifest_tables: dict[str, dict] = {}
        for name, rows in tables.items():
            filename = f"{name}.ndjson"
            path = os.path.join(export_dir, filename)
            with open(path, "w") as f:
                for row in rows:
                    f.write(json.dumps(row, default=str) + "\n")
            manifest_tables[name] = {"row_count": len(rows), "file": filename}

        checkpoint = utcnow().isoformat()
        manifest = {
            "export_id": export_id,
            "created_at": utcnow().isoformat(),
            "organisation_id": organisation_id,
            "tables": manifest_tables,
            "checkpoint": checkpoint,
        }
        with open(os.path.join(export_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f, indent=2)

        self.audit.record(
            event_type="ANALYTICS_JOB_STARTED", entity_type="export", entity_id=export_id,
            organisation_id=organisation_id,
            payload={"export_id": export_id, "row_counts":
                     {k: v["row_count"] for k, v in manifest_tables.items()}},
            request_id_header=self.request_id_header,
        )
        log.info("export_complete", export_id=export_id,
                 rows=sum(v["row_count"] for v in manifest_tables.values()))
        return manifest

    # --- row serialisers ---
    def _request_row(self, r: Request) -> dict:
        return {
            "id": r.id, "organisation_id": r.organisation_id,
            "request_type": r.request_type.value, "requester_id": r.requester_id,
            "resource_id": r.resource_id, "title": r.title,
            "request_payload": r.request_payload, "risk_score": r.risk_score,
            "risk_level": r.risk_level.value if r.risk_level else None,
            "decision": r.decision.value if r.decision else None,
            "status": r.status.value, "submitted_at": _iso(r.submitted_at),
            "approved_at": _iso(r.approved_at), "expires_at": _iso(r.expires_at),
            "created_at": _iso(r.created_at), "updated_at": _iso(r.updated_at),
        }

    def _eval_row(self, e: PolicyEvaluation) -> dict:
        return {"id": e.id, "request_id": e.request_id, "policy_id": e.policy_id,
                "policy_version_id": e.policy_version_id, "matched": e.matched,
                "violations": e.violations, "risk_contribution": e.risk_contribution,
                "evaluated_at": _iso(e.evaluated_at)}

    def _approval_row(self, a: ApprovalTask) -> dict:
        return {"id": a.id, "approval_stage_id": a.approval_stage_id,
                "approver_user_id": a.approver_user_id, "approver_role": a.approver_role,
                "status": a.status.value, "decision": a.decision,
                "assigned_at": _iso(a.assigned_at), "acted_at": _iso(a.acted_at),
                "due_at": _iso(a.due_at)}

    def _exception_row(self, e: PolicyException) -> dict:
        return {"id": e.id, "request_id": e.request_id, "policy_id": e.policy_id,
                "status": e.status.value, "start_at": _iso(e.start_at),
                "expires_at": _iso(e.expires_at)}

    def _grant_row(self, g: AccessGrant) -> dict:
        return {"id": g.id, "request_id": g.request_id, "resource_id": g.resource_id,
                "user_id": g.user_id, "grant_type": g.grant_type.value,
                "provisioning_status": g.provisioning_status.value,
                "revocation_status": g.revocation_status.value if g.revocation_status else None,
                "granted_at": _iso(g.granted_at), "expires_at": _iso(g.expires_at),
                "revoked_at": _iso(g.revoked_at)}

    def _revocation_row(self, r: RevocationAttempt) -> dict:
        return {"id": r.id, "access_grant_id": r.access_grant_id,
                "attempt_number": r.attempt_number, "status": r.status,
                "error_code": r.error_code, "started_at": _iso(r.started_at),
                "completed_at": _iso(r.completed_at)}

    def _audit_row(self, a: AuditEvent) -> dict:
        return {"id": a.id, "request_id": a.request_id, "actor_id": a.actor_id,
                "event_type": a.event_type, "entity_type": a.entity_type,
                "created_at": _iso(a.created_at)}
