from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models.enums import RequestType
from app.models.org import User
from app.models.policy import Policy
from app.policy_engine import PolicyEngine
from app.policy_engine.context_builder import build_context, load_active_policies
from app.risk_engine import RiskEngine

router = APIRouter(prefix="/policies", tags=["policies"])


class PolicyOut(BaseModel):
    id: str
    name: str
    description: str | None
    policy_type: str
    priority: int
    status: str
    version: int
    owner_user_id: str | None

    class Config:
        from_attributes = True


def _out(p: Policy) -> PolicyOut:
    return PolicyOut(
        id=p.id, name=p.name, description=p.description, policy_type=p.policy_type.value,
        priority=p.priority, status=p.status.value, version=p.version, owner_user_id=p.owner_user_id,
    )


@router.get("", response_model=list[PolicyOut])
def list_policies(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    stmt = select(Policy).where(Policy.organisation_id == user.organisation_id)
    return [_out(p) for p in db.execute(stmt).scalars().all()]


@router.get("/{policy_id}", response_model=PolicyOut)
def get_policy(policy_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    p = db.get(Policy, policy_id)
    if not p or p.organisation_id != user.organisation_id:
        raise NotFoundError("Policy not found.")
    return _out(p)


class EvaluateTestRequest(BaseModel):
    request_type: RequestType
    resource_id: str | None = None
    requester_id: str | None = None
    payload: dict = {}


@router.post("/evaluate-test")
def evaluate_test(
    body: EvaluateTestRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Run the deterministic engine + risk engine against published policies.

    Read-only: no request is persisted. Powers the 'Review policy evaluation'
    step of the New Request wizard.
    """
    context = build_context(
        db,
        request_type=body.request_type.value,
        payload=body.payload,
        resource_id=body.resource_id,
        requester_id=body.requester_id or user.id,
    )
    active = load_active_policies(db, user.organisation_id)
    decision = PolicyEngine().evaluate_request(context, active)
    risk = RiskEngine().score(context.as_dict(), decision.risk_contributions)

    response = decision.to_response()
    response["risk_score"] = risk.risk_score
    response["risk_level"] = risk.risk_level
    response["risk_factors"] = [{"name": f.name, "points": f.points} for f in risk.factors]
    return response
