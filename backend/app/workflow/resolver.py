"""Resolve required approver roles to concrete users.

Resolution order for a role:
  1. MANAGER          -> the requester's manager (manager-chain lookup)
  2. DATA_OWNER       -> the target resource's owner, else any data owner
  3. others by role   -> any active user holding that role in the organisation

Conflict-of-interest: the requester is never selected as their own approver.
If no user can be found for a role, an unassigned task is created with the role
recorded, so the stage still exists and can be reassigned later.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import Role, UserStatus
from app.models.org import Resource, User


def resolve_approver(
    db: Session,
    *,
    role: str,
    organisation_id: str,
    requester: User,
    resource: Resource | None,
) -> str | None:
    """Return a user id to assign for this role, or None if unassignable."""
    if role == Role.MANAGER.value:
        if requester.manager_id and requester.manager_id != requester.id:
            return requester.manager_id
        # fall through to any manager if no direct manager

    if role == Role.DATA_OWNER.value and resource and resource.owner_user_id:
        if resource.owner_user_id != requester.id:
            return resource.owner_user_id

    # Generic: any active user with the role, excluding the requester.
    stmt = (
        select(User)
        .where(
            User.organisation_id == organisation_id,
            User.role == Role(role),
            User.status == UserStatus.ACTIVE,
            User.id != requester.id,
        )
        .limit(1)
    )
    user = db.execute(stmt).scalar_one_or_none()
    return user.id if user else None
