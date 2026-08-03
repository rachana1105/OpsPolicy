"""Transparent, deterministic risk scoring.

Risk is computed from (a) intrinsic request attributes and (b) risk points
contributed by matched policies. Every factor is returned in a breakdown so the
score is fully explainable.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.policy_engine.types import RiskContribution


@dataclass
class RiskFactor:
    name: str
    points: int


@dataclass
class RiskResult:
    risk_score: int
    risk_level: str
    factors: list[RiskFactor]

    def to_response(self) -> dict:
        return {
            "risk_score": self.risk_score,
            "risk_level": self.risk_level,
            "factors": [{"name": f.name, "points": f.points} for f in self.factors],
        }


def level_for_score(score: int) -> str:
    if score >= 20:
        return "CRITICAL"
    if score >= 12:
        return "HIGH"
    if score >= 6:
        return "MEDIUM"
    return "LOW"


class RiskEngine:
    APPROVED_REGIONS = {"IN", "SG"}

    def score(
        self,
        context: dict,
        policy_contributions: list[RiskContribution] | None = None,
        history: dict | None = None,
    ) -> RiskResult:
        # TODO: compute risk factors from the request context — resource
        # sensitivity/criticality, requested action (e.g. EXPORT),
        # destination region vs APPROVED_REGIONS, duration, requester type,
        # emergency flag, purchase amount thresholds, and prior-exception /
        # prior-revocation-failure history — plus any policy-contributed risk
        # points, then sum into a RiskResult (score, level via
        # level_for_score, and the itemised factor breakdown).
        raise NotImplementedError
