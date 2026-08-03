"""Simulated provisioning service.

No real Okta / SAP / ServiceNow / cloud IAM in v1. This simulates granting and
revoking access with deterministic-but-varied outcomes so the whole lifecycle —
success, temporary failure, permanent failure, timeout, duplicate callback — is
exercised end to end.

Idempotency key: request_id + grant_type + resource_id + user_id (enforced by a
DB unique constraint on AccessGrant, and re-checked here).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from app.models.enums import GrantType, RequestType


@dataclass
class ProvisionOutcome:
    status: str  # SUCCEEDED | FAILED
    external_reference: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    permanent: bool = False


# Grant type derived from the request.
def grant_type_for(request_type: str, payload: dict) -> GrantType:
    if request_type == RequestType.DATASET_ACCESS.value:
        action = payload.get("requested_action")
        return GrantType.GRANT_DATASET_EXPORT if action == "EXPORT" else GrantType.GRANT_DATASET_READ
    if request_type == RequestType.PRODUCTION_ACCESS.value:
        role = payload.get("requested_role")
        return GrantType.GRANT_PRODUCTION_ADMIN if role == "ADMIN" else GrantType.GRANT_PRODUCTION_READ
    return GrantType.APPROVE_PURCHASE


def _deterministic_bucket(seed: str, mod: int) -> int:
    """Stable pseudo-random bucket from a seed, so behaviour is reproducible."""
    digest = hashlib.sha256(seed.encode()).hexdigest()
    return int(digest[:8], 16) % mod


class SimulatedProvisioningService:
    """Deterministic simulation. `force_*` flags let tests pin behaviour."""

    def provision(
        self,
        *,
        grant_id: str,
        grant_type: GrantType,
        resource_id: str | None,
        user_id: str,
        force_outcome: str | None = None,
    ) -> ProvisionOutcome:
        # TODO: honor force_outcome ("fail_permanent" | "fail_temporary" |
        # "succeed") for tests, otherwise use _deterministic_bucket(grant_id)
        # so ~95% of grants succeed and the rest fail with a temporary error.
        raise NotImplementedError

    def revoke(
        self,
        *,
        grant_id: str,
        attempt_number: int,
        force_outcome: str | None = None,
    ) -> ProvisionOutcome:
        # TODO: honor force_outcome ("fail" | "succeed") for tests, otherwise
        # use _deterministic_bucket(grant_id) so most revocations succeed
        # immediately and a "sticky" subset fails the first two attempts
        # before succeeding, to exercise the retry ladder in demos.
        raise NotImplementedError
