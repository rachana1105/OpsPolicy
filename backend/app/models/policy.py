"""Policy and versioned policy definitions."""
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.types import UTCDateTime
from app.db.base import Base, TimestampMixin, UUIDMixin, utcnow
from app.models.enums import PolicyStatus, PolicyType


class Policy(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "policies"
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_type: Mapped[PolicyType] = mapped_column(default=PolicyType.GENERAL, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    status: Mapped[PolicyStatus] = mapped_column(default=PolicyStatus.DRAFT, nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    effective_from: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    effective_until: Mapped[datetime | None] = mapped_column(UTCDateTime, nullable=True)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    # points to the currently published version
    published_version_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class PolicyVersion(Base, UUIDMixin):
    __tablename__ = "policy_versions"
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    definition_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDateTime, nullable=False, default=utcnow
    )
