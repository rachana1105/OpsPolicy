"""Explicit allowed state transitions for requests.

Any transition not listed is rejected with a structured error.
"""
from app.core.errors import InvalidStateTransitionError
from app.models.enums import RequestStatus as R

ALLOWED_REQUEST_TRANSITIONS: dict[R, set[R]] = {
    R.DRAFT: {R.SUBMITTED, R.CANCELLED},
    R.SUBMITTED: {R.EVALUATING, R.CANCELLED},
    R.EVALUATING: {R.UNDER_REVIEW, R.APPROVED, R.REJECTED},
    R.UNDER_REVIEW: {
        R.PARTIALLY_APPROVED,
        R.APPROVED,
        R.REJECTED,
        R.CHANGES_REQUESTED,
        R.CANCELLED,
    },
    R.PARTIALLY_APPROVED: {R.APPROVED, R.REJECTED, R.UNDER_REVIEW},
    R.CHANGES_REQUESTED: {R.SUBMITTED, R.CANCELLED},
    R.APPROVED: {R.PROVISIONING, R.CANCELLED},
    R.PROVISIONING: {R.ACTIVE, R.REVOCATION_FAILED},
    R.ACTIVE: {R.EXPIRING, R.CLOSED},
    R.EXPIRING: {R.REVOKED, R.REVOCATION_FAILED},
    R.REVOCATION_FAILED: {R.EXPIRING, R.ESCALATED},
    R.ESCALATED: {R.REVOKED, R.CLOSED},
    R.REVOKED: {R.CLOSED},
    R.REJECTED: set(),
    R.CANCELLED: set(),
    R.CLOSED: set(),
}


def assert_transition(current: R, target: R) -> None:
    allowed = ALLOWED_REQUEST_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidStateTransitionError(
            message=f"A {current.value} request cannot transition to {target.value}.",
            details={"current_state": current.value, "requested_state": target.value},
        )
