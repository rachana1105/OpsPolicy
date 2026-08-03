"""Value objects used by the policy engine (framework-independent)."""
from dataclasses import dataclass, field
from typing import Any


@dataclass
class RequestContext:
    """Flattened, engine-friendly view of a request and its subject entities."""
    request: dict[str, Any]
    resource: dict[str, Any] = field(default_factory=dict)
    requester: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "request": self.request,
            "resource": self.resource,
            "requester": self.requester,
        }


@dataclass
class RequiredApproval:
    role: str
    stage: int

    def key(self) -> tuple[str, int]:
        return (self.role, self.stage)


@dataclass
class RiskContribution:
    name: str
    points: int
    reason: str = ""
    source_policy: str = ""


@dataclass
class MatchedPolicy:
    policy_id: str
    policy_version_id: str
    name: str
    priority: int
    violations: list[str] = field(default_factory=list)
    required_actions: list[dict] = field(default_factory=list)
    risk_contribution: int = 0


@dataclass
class PolicyDecision:
    decision: str  # AUTO_APPROVE | REQUIRES_APPROVAL | REJECT | REQUIRES_EXCEPTION
    matched_policies: list[MatchedPolicy] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)
    required_approval_stages: list[RequiredApproval] = field(default_factory=list)
    risk_contributions: list[RiskContribution] = field(default_factory=list)
    maximum_duration: int | None = None
    required_evidence: list[str] = field(default_factory=list)
    automatic_actions: list[dict] = field(default_factory=list)
    explanation: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)

    def to_response(self) -> dict:
        return {
            "decision": self.decision,
            "matched_policies": [m.name for m in self.matched_policies],
            "violations": self.violations,
            "required_approvals": [
                {"role": a.role, "stage": a.stage} for a in self.required_approval_stages
            ],
            "risk_contributions": [
                {"name": r.name, "points": r.points, "reason": r.reason}
                for r in self.risk_contributions
            ],
            "maximum_allowed_duration_days": self.maximum_duration,
            "required_evidence": self.required_evidence,
            "automatic_actions": self.automatic_actions,
            "explanation": self.explanation,
            "conflicts": self.conflicts,
        }
