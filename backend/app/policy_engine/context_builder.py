"""Build an engine RequestContext from DB entities or a raw payload."""
from sqlalchemy.orm import Session

from app.models.enums import PolicyStatus
from app.models.org import Resource, User
from app.models.policy import Policy, PolicyVersion
from app.policy_engine.engine import ActivePolicy
from app.policy_engine.types import RequestContext


def build_context(
    db: Session,
    *,
    request_type: str,
    payload: dict,
    resource_id: str | None,
    requester_id: str | None,
) -> RequestContext:
    request_view = dict(payload)
    request_view["request_type"] = request_type

    resource_view: dict = {}
    if resource_id:
        resource = db.get(Resource, resource_id)
        if resource:
            resource_view = {
                "sensitivity": resource.sensitivity.value,
                "criticality": resource.criticality.value,
                "region": resource.region,
                "resource_type": resource.resource_type.value,
                "owner_user_id": resource.owner_user_id,
            }

    requester_view: dict = {}
    if requester_id:
        requester = db.get(User, requester_id)
        if requester:
            requester_view = {
                "employee_type": requester.employee_type.value,
                "role": requester.role.value,
                "team_id": requester.team_id,
                "manager_id": requester.manager_id,
            }

    return RequestContext(
        request=request_view, resource=resource_view, requester=requester_view
    )


def load_active_policies(db: Session, organisation_id: str) -> list[ActivePolicy]:
    """Load published policies with their currently published version."""
    policies = (
        db.query(Policy)
        .filter(
            Policy.organisation_id == organisation_id,
            Policy.status == PolicyStatus.PUBLISHED,
            Policy.published_version_id.isnot(None),
        )
        .all()
    )
    active: list[ActivePolicy] = []
    for policy in policies:
        version = db.get(PolicyVersion, policy.published_version_id)
        if not version:
            continue
        active.append(
            ActivePolicy(
                policy_id=policy.id,
                policy_version_id=version.id,
                name=policy.name,
                priority=policy.priority,
                definition=version.definition_json,
            )
        )
    return active
