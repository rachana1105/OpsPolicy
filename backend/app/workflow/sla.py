"""SLA deadlines per approver role, in hours.

Kept small and configurable so demos show escalation quickly. Emergency
requests compress these further (handled in the workflow builder).
"""
from app.models.enums import Role

SLA_HOURS: dict[str, int] = {
    Role.MANAGER.value: 8,
    Role.DATA_OWNER.value: 24,
    Role.SECURITY_REVIEWER.value: 24,
    Role.FINANCE_REVIEWER.value: 24,
    Role.DEPARTMENT_HEAD.value: 24,
    Role.COMPLIANCE_OFFICER.value: 48,
}

EMERGENCY_SLA_HOURS = 0.5  # 30 minutes for emergency requests


def sla_hours_for(role: str, emergency: bool = False) -> float:
    if emergency:
        return EMERGENCY_SLA_HOURS
    return SLA_HOURS.get(role, 24)
