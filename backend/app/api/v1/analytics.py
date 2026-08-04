from datetime import datetime

from fastapi import APIRouter, Depends, Request as FastAPIRequest
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.org import User
from app.services.analytics_service import AnalyticsService

router = APIRouter(tags=["analytics"])


def _svc(req: FastAPIRequest, db: Session) -> AnalyticsService:
    return AnalyticsService(db, request_id_header=getattr(req.state, "request_id", None))


# ---- compliance ----

@router.get("/analytics/compliance-summary")
def compliance_summary(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = AnalyticsService(db)
    job = svc.latest_compliance(user.organisation_id)
    if not job:
        return {"available": False, "message": "No compliance refresh has run yet."}
    return {
        "available": True,
        "data_freshness": job.completed_at.isoformat() if job.completed_at else None,
        "external_job_id": job.external_job_id,
        **(job.result_payload or {}),
    }


@router.post("/analytics/refresh")
def refresh(req: FastAPIRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    svc = _svc(req, db)
    job = svc.refresh_compliance(user.organisation_id)
    db.commit()
    return {"job_id": job.id, "status": job.status.value,
            "data_freshness": job.completed_at.isoformat() if job.completed_at else None}


@router.get("/analytics/approval-sla")
def approval_sla(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = AnalyticsService(db).latest_compliance(user.organisation_id)
    if not job:
        return {"available": False}
    return {"available": True, **(job.result_payload or {}).get("approval_sla", {})}


@router.get("/analytics/department-risk")
def department_risk(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = AnalyticsService(db).latest_compliance(user.organisation_id)
    if not job:
        return {"available": False}
    return {"available": True, **(job.result_payload or {}).get("department_risk", {})}


@router.get("/analytics/revocation-failures")
def revocation_failures(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = AnalyticsService(db).latest_compliance(user.organisation_id)
    if not job:
        return {"available": False}
    return {"available": True, **(job.result_payload or {}).get("revocation_failures", {})}


@router.get("/analytics/exception-trends")
def exception_trends(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = AnalyticsService(db).latest_compliance(user.organisation_id)
    if not job:
        return {"available": False}
    return {"available": True, **(job.result_payload or {}).get("exception_trends", {})}


# ---- policy simulations ----

class SimulationCreate(BaseModel):
    policy_definition: dict
    start_date: datetime | None = None
    end_date: datetime | None = None


def _job_out(job) -> dict:
    return {
        "id": job.id, "status": job.status.value, "job_type": job.job_type.value,
        "external_job_id": job.external_job_id, "input_reference": job.input_reference,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "result": job.result_payload,
    }


@router.post("/policy-simulations")
def create_simulation(
    body: SimulationCreate, req: FastAPIRequest,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    svc = _svc(req, db)
    job = svc.create_simulation(
        user.organisation_id, policy_definition=body.policy_definition,
        start_date=body.start_date, end_date=body.end_date,
    )
    db.commit()
    return _job_out(job)


@router.get("/policy-simulations")
def list_simulations(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    jobs = AnalyticsService(db).list_simulations(user.organisation_id)
    return [_job_out(j) for j in jobs]


@router.get("/policy-simulations/{simulation_id}")
def get_simulation(simulation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = AnalyticsService(db).get_job(simulation_id, user.organisation_id)
    return _job_out(job)


@router.get("/policy-simulations/{simulation_id}/status")
def simulation_status(simulation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = AnalyticsService(db).get_job(simulation_id, user.organisation_id)
    return {"id": job.id, "status": job.status.value}


@router.get("/policy-simulations/{simulation_id}/result")
def simulation_result(simulation_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    job = AnalyticsService(db).get_job(simulation_id, user.organisation_id)
    if not job.result_payload:
        raise NotFoundError("Simulation result not ready.")
    return job.result_payload
