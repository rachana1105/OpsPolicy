"""Deterministic policy evaluation engine.

The engine takes a request context plus a set of active policy versions and
produces a single, explainable decision. It never executes arbitrary code and
is fully deterministic: the same inputs always yield the same output.

Conflict resolution rules (per spec):
  1. Explicit rejection overrides auto-approval.
  2. The strictest maximum duration wins.
  3. Required approvers from multiple matching policies are merged.
  4. Duplicate approver roles do not create duplicate tasks in the same stage.
  5. Higher-risk policies can add approval stages.
  6. Policy conflicts are surfaced in the result.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.policy_engine.conditions import evaluate_conditions
from app.policy_engine.types import (
    MatchedPolicy,
    PolicyDecision,
    RequestContext,
    RequiredApproval,
    RiskContribution,
)


@dataclass
class ActivePolicy:
    """A published policy version fed to the engine."""
    policy_id: str
    policy_version_id: str
    name: str
    priority: int
    definition: dict


class PolicyEngine:
    def evaluate_request(
        self,
        request_context: RequestContext,
        active_policies: list[ActivePolicy],
    ) -> PolicyDecision:
        # TODO: evaluate active_policies in priority order against the request
        # context. For each matching policy, apply its actions (require
        # approval, set max duration, add risk, reject, require exception,
        # require evidence, add violation, automatic action) per the conflict
        # resolution rules documented above, then derive the final decision
        # (REJECT > REQUIRES_EXCEPTION > REQUIRES_APPROVAL > AUTO_APPROVE)
        # and run conflict detection before returning.
        raise NotImplementedError

    @staticmethod
    def _applies_to(applies: dict, context: dict) -> bool:
        # TODO: check whether a policy's `applies_to` scope matches the
        # request context (e.g. request_type).
        raise NotImplementedError

    @staticmethod
    def _detect_conflicts(decision: PolicyDecision) -> None:
        # TODO: surface conflicting signals in the decision, e.g. a rejection
        # alongside policies that would otherwise have required approval.
        raise NotImplementedError
