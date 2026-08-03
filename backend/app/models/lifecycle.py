"""Exceptions, access grants, revocation, audit and analytics job models."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import UTCDateTime
from app.db.base import Base, TimestampMixin, UUIDMixin, utcnow
from app.models.enums import (
    AnalyticsJobStatus,
    AnalyticsJobType,
    ExceptionStatus,
    GrantType,
    ProvisioningStatus,
    RevocationStatus,
)


class PolicyException(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "policy_exceptions"
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), nullable=False)
    policy_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    requested_by: Mapped[str] = mapped_column(String(36), nullable=False)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    risk_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    compensating_controls: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(UTCDateTime, nullable=False)
    status: Mapped[ExceptionStatus] = mapped_column(default=ExceptionStatus.REQUESTED, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)


class AccessGrant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "access_grants"
    __table_args__ = (
        UniqueConstraint(
            "request_id", "grant_type", "resource_id", "user_id",
            name="uq_grant_idempotency",
        ),
    )
    request_id: Mapped[str] = mapped_column(ForeignKey("requests.id"), nullable=False)
    resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    grant_type: Mapped[GrantType] = mapped_column(nullable=False)
    provisioning_status: Mapped[ProvisioningStatus] = mapped_column(
        default=ProvisioningStatus.PENDING, nullable=False
    )
    revocation_status: Mapped[RevocationStatus | None] = mapped_column(nullable=True)
    granted_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    external_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lock_version: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class RevocationAttempt(Base, UUIDMixin):
    __tablename__ = "revocation_attempts"
    access_grant_id: Mapped[str] = mapped_column(ForeignKey("access_grants.id"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    next_retry_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class AuditEvent(Base, UUIDMixin):
    """Append-only. Never update after insert."""
    __tablename__ = "audit_events"
    organisation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    request_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    actor_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    previous_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    new_state: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    request_id_header: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, nullable=False)


class AnalyticsJob(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "analytics_jobs"
    organisation_id: Mapped[str] = mapped_column(String(36), nullable=False)
    job_type: Mapped[AnalyticsJobType] = mapped_column(nullable=False)
    external_job_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[AnalyticsJobStatus] = mapped_column(default=AnalyticsJobStatus.QUEUED, nullable=False)
    input_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result_reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    result_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)


class Notification(Base, UUIDMixin):
    __tablename__ = "notifications"
    user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    notification_type: Mapped[str] = mapped_column(String(64), nullable=False)
    subject: Mapped[str] = mapped_column(String(255), nullable=False)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING")
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    dedupe_key: Mapped[str | None] = mapped_column(String(255), nullable=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
