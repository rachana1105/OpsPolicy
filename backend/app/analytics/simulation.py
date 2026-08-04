"""Historical policy simulation (Milestone 7 — the flagship analytics feature).

Given a proposed policy definition and a historical window, re-evaluate past
requests with the SAME deterministic engine used for live decisions, and
quantify the impact: how many requests would be affected, how many previously
approved would now be rejected or need shorter durations, and the breakdown by
department and risk. Because the engine is a pure function, the simulation is
exactly consistent with what would happen in production.

In a real deployment this runs as a Databricks job over Delta tables; the logic
here mirrors that job so results match and local demos need no live account.
"""
from __future__ import annotations

from collections import Counter, defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import utcnow
from app.models.enums import Decision, RequestStatus
from app.models.org import Resource, User
from app.models.request import Request
from app.policy_engine.engine import ActivePolicy, PolicyEngine
from app.policy_engine.types import RequestContext


def _context_for(db: Session, req: Request) -> RequestContext:
    request_view = dict(req.request_payload)
    request_view["request_type"] = req.request_type.value
    resource_view: dict = {}
    if req.resource_id:
        r = db.get(Resource, req.resource_id)
        if r:
            resource_view = {
                "sensitivity": r.sensitivity.value, "criticality": r.criticality.value,
                "region": r.region, "resource_type": r.resource_type.value,
                "owner_user_id": r.owner_user_id,
            }
    requester_view: dict = {}
    u = db.get(User, req.requester_id)
    if u:
        requester_view = {"employee_type": u.employee_type.value, "role": u.role.value,
                          "team_id": u.team_id, "manager_id": u.manager_id}
    return RequestContext(request=request_view, resource=resource_view, requester=requester_view)


def run_simulation(
    db: Session,
    organisation_id: str,
    *,
    simulation_id: str,
    policy_definition: dict,
    start_date=None,
    end_date=None,
) -> dict:
    # TODO: replay all non-draft historical requests (optionally filtered by
    # date range) through PolicyEngine with the proposed policy as the only
    # active policy. For each request, detect whether the proposed policy
    # would change the outcome (new rejection/exception, a tighter max
    # duration than what was requested, or new required approvals),
    # tallying affected counts, previously-approved-now-rejected counts,
    # duration reductions, per-team impact, and risk distribution. Derive a
    # recommendation (NO_HISTORICAL_DATA / HIGH_IMPACT_REVIEW_BEFORE_ROLLOUT /
    # INTRODUCE_GRADUALLY / SAFE_TO_INTRODUCE) from the impact ratios, and
    # return the full simulation summary dict.
    raise NotImplementedError
