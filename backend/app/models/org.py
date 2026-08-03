"""Organisation hierarchy: Organisation, BusinessUnit, Department, Team, User, Resource."""
from sqlalchemy import Boolean, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models.enums import (
    Criticality,
    EmployeeType,
    ResourceType,
    Role,
    Sensitivity,
    UserStatus,
)


class Organisation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "organisations"
    name: Mapped[str] = mapped_column(String(255), nullable=False)


class BusinessUnit(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "business_units"
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    head_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class Department(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "departments"
    business_unit_id: Mapped[str] = mapped_column(ForeignKey("business_units.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    head_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class Team(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "teams"
    department_id: Mapped[str] = mapped_column(ForeignKey("departments.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    manager_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), nullable=False)
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    manager_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    employee_type: Mapped[EmployeeType] = mapped_column(default=EmployeeType.EMPLOYEE, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[Role] = mapped_column(default=Role.EMPLOYEE, nullable=False)
    status: Mapped[UserStatus] = mapped_column(default=UserStatus.ACTIVE, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)


class Resource(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "resources"
    organisation_id: Mapped[str] = mapped_column(ForeignKey("organisations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[ResourceType] = mapped_column(nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    criticality: Mapped[Criticality] = mapped_column(default=Criticality.MEDIUM, nullable=False)
    sensitivity: Mapped[Sensitivity] = mapped_column(default=Sensitivity.INTERNAL, nullable=False)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    resource_metadata: Mapped[dict] = mapped_column("metadata", JSON, default=dict)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
