"""Safe, deterministic condition evaluation for policy definitions.

No arbitrary code execution. Conditions reference request-context fields by
dotted path and compare them with a fixed operator set.
"""
from typing import Any


class ConditionError(ValueError):
    """Raised when a policy condition is malformed."""


def resolve_field(context: dict, path: str) -> Any:
    """Resolve a dotted path such as 'resource.sensitivity' against the context."""
    current: Any = context
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
        if current is None:
            return None
    return current


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None


OPERATORS = {
    "EQUALS",
    "NOT_EQUALS",
    "IN",
    "NOT_IN",
    "GREATER_THAN",
    "GREATER_THAN_OR_EQUAL",
    "LESS_THAN",
    "LESS_THAN_OR_EQUAL",
    "CONTAINS",
    "IS_NULL",
    "IS_NOT_NULL",
}


def evaluate_leaf(condition: dict, context: dict) -> bool:
    """Evaluate a single field/operator/value condition."""
    # TODO: resolve `condition["field"]` against context and compare it to
    # `condition["value"]` using `condition["operator"]` (see OPERATORS).
    # Numeric operators should coerce both sides via _as_number first.
    raise NotImplementedError


def evaluate_conditions(node: dict | None, context: dict) -> bool:
    """Recursively evaluate a condition group (all / any / not) or a leaf.

    An empty or missing node matches everything (applies_to already gated it).
    """
    # TODO: recursively evaluate "all" (AND), "any" (OR), and "not" groups,
    # falling through to evaluate_leaf for a plain condition node.
    raise NotImplementedError
