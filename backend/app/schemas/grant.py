from datetime import datetime

from pydantic import BaseModel


class AccessGrantOut(BaseModel):
    id: str
    request_id: str
    resource_id: str | None
    user_id: str
    grant_type: str
    provisioning_status: str
    revocation_status: str | None
    granted_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None
    external_reference: str | None

    class Config:
        from_attributes = True


class RevocationAttemptOut(BaseModel):
    id: str
    attempt_number: int
    status: str
    error_code: str | None
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
    next_retry_at: datetime | None

    class Config:
        from_attributes = True
