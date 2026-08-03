"""Analytics orchestration service (Milestone 7).

Bridges the operational platform and the analytics engine. Compliance metrics
and simulations are recorded as AnalyticsJob rows so the UI can show status and
data freshness. The core platform never blocks on this: if analytics is
unavailable, submission/approval/provisioning continue and the dashboard shows a
stale state.

Two execution modes:
  * mock (default, local): compute metrics/simulation directly from the DB using
    the same deterministic engine, so results are real and need no Databricks.
  * databricks: submit to Databricks Jobs via the provider and poll status.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analytics.metrics import (
    compute_approval_sla,
    compute_compliance_summary,
    compute_department_risk,
    compute_exception_trends,
    compute_revocation_failures,
)
from app.analytics.simulation import run_simulation
from app.audit.service import AuditService
from app.core.config import settings
from app.core.errors import NotFoundError
from app.core.logging import get_logger
from app.db.base import utcnow
from app.models.enums import AnalyticsJobStatus, AnalyticsJobType
from app.models.lifecycle import AnalyticsJob

log = get_logger("analytics")


class AnalyticsService:
    def __init__(self, db: Session, request_id_header: str | None = None):
        self.db = db
        self.audit = AuditService(db)
        self.request_id_header = request_id_header
        self.provider_kind = settings.analytics_provider

    # ---- compliance refresh ----

    def refresh_compliance(self, organisation_id: str) -> AnalyticsJob:
        job = AnalyticsJob(
            organisation_id=organisation_id, job_type=AnalyticsJobType.COMPLIANCE_REFRESH,
            status=AnalyticsJobStatus.RUNNING, started_at=utcnow(),
        )
        self.db.add(job)
        self.db.flush()
        self.audit.record(
            event_type="ANALYTICS_JOB_STARTED", entity_type="analytics_job", entity_id=job.id,
            organisation_id=organisation_id, payload={"job_type": "COMPLIANCE_REFRESH"},
            request_id_header=self.request_id_header,
        )
        try:
            payload = {
                "compliance_summary": compute_compliance_summary(self.db, organisation_id),
                "approval_sla": compute_approval_sla(self.db, organisation_id),
                "department_risk": compute_department_risk(self.db, organisation_id),
                "revocation_failures": compute_revocation_failures(self.db, organisation_id),
                "exception_trends": compute_exception_trends(self.db, organisation_id),
            }
            job.result_payload = payload
            job.status = AnalyticsJobStatus.SUCCEEDED
            job.completed_at = utcnow()
            job.external_job_id = f"local-refresh-{job.id[:8]}"
            self.audit.record(
                event_type="ANALYTICS_JOB_COMPLETED", entity_type="analytics_job",
                entity_id=job.id, organisation_id=organisation_id,
                payload={"job_type": "COMPLIANCE_REFRESH"},
                request_id_header=self.request_id_header,
            )
        except Exception as exc:  # noqa: BLE001
            job.status = AnalyticsJobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = utcnow()
            log.error("compliance_refresh_failed", error=str(exc))
        self.db.flush()
        return job

    def latest_compliance(self, organisation_id: str) -> AnalyticsJob | None:
        return self.db.execute(
            select(AnalyticsJob)
            .where(AnalyticsJob.organisation_id == organisation_id,
                   AnalyticsJob.job_type == AnalyticsJobType.COMPLIANCE_REFRESH,
                   AnalyticsJob.status == AnalyticsJobStatus.SUCCEEDED)
            .order_by(AnalyticsJob.completed_at.desc())
        ).scalars().first()

    # ---- policy simulation ----

    def create_simulation(
        self, organisation_id: str, *, policy_definition: dict,
        start_date=None, end_date=None,
    ) -> AnalyticsJob:
        job = AnalyticsJob(
            organisation_id=organisation_id, job_type=AnalyticsJobType.POLICY_SIMULATION,
            status=AnalyticsJobStatus.RUNNING, started_at=utcnow(),
            input_reference=policy_definition.get("name", "proposed"),
        )
        self.db.add(job)
        self.db.flush()
        self.audit.record(
            event_type="ANALYTICS_JOB_STARTED", entity_type="analytics_job", entity_id=job.id,
            organisation_id=organisation_id, payload={"job_type": "POLICY_SIMULATION"},
            request_id_header=self.request_id_header,
        )
        try:
            result = run_simulation(
                self.db, organisation_id, simulation_id=job.id,
                policy_definition=policy_definition, start_date=start_date, end_date=end_date,
            )
            job.result_payload = result
            job.status = AnalyticsJobStatus.SUCCEEDED
            job.completed_at = utcnow()
            job.external_job_id = f"local-sim-{job.id[:8]}"
            self.audit.record(
                event_type="ANALYTICS_JOB_COMPLETED", entity_type="analytics_job",
                entity_id=job.id, organisation_id=organisation_id,
                payload={"job_type": "POLICY_SIMULATION",
                         "requests_affected": result["requests_affected"]},
                request_id_header=self.request_id_header,
            )
        except Exception as exc:  # noqa: BLE001
            job.status = AnalyticsJobStatus.FAILED
            job.error_message = str(exc)
            job.completed_at = utcnow()
            log.error("simulation_failed", error=str(exc))
        self.db.flush()
        return job

    def get_job(self, job_id: str, organisation_id: str) -> AnalyticsJob:
        job = self.db.get(AnalyticsJob, job_id)
        if not job or job.organisation_id != organisation_id:
            raise NotFoundError("Analytics job not found.")
        return job

    def list_simulations(self, organisation_id: str) -> list[AnalyticsJob]:
        return list(self.db.execute(
            select(AnalyticsJob)
            .where(AnalyticsJob.organisation_id == organisation_id,
                   AnalyticsJob.job_type == AnalyticsJobType.POLICY_SIMULATION)
            .order_by(AnalyticsJob.created_at.desc())
        ).scalars().all())
