"""Unit tests for the deterministic policy engine and conditions."""
from app.policy_engine.conditions import evaluate_conditions, evaluate_leaf
from app.policy_engine.engine import ActivePolicy, PolicyEngine
from app.policy_engine.types import RequestContext


def ctx(**request):
    resource = request.pop("_resource", {})
    requester = request.pop("_requester", {})
    return RequestContext(request=request, resource=resource, requester=requester)


# ---- operators ----

def test_equals_and_not_equals():
    c = {"request": {"a": "X"}}
    assert evaluate_leaf({"field": "request.a", "operator": "EQUALS", "value": "X"}, c)
    assert not evaluate_leaf({"field": "request.a", "operator": "NOT_EQUALS", "value": "X"}, c)


def test_numeric_operators():
    c = {"request": {"amount": 1200000}}
    assert evaluate_leaf({"field": "request.amount", "operator": "GREATER_THAN", "value": 1000000}, c)
    assert not evaluate_leaf({"field": "request.amount", "operator": "LESS_THAN", "value": 1000000}, c)
    assert evaluate_leaf({"field": "request.amount", "operator": "GREATER_THAN_OR_EQUAL", "value": 1200000}, c)


def test_in_and_not_in():
    c = {"request": {"region": "US"}}
    assert evaluate_leaf({"field": "request.region", "operator": "NOT_IN", "value": ["IN", "SG"]}, c)
    assert not evaluate_leaf({"field": "request.region", "operator": "IN", "value": ["IN", "SG"]}, c)


def test_null_operators():
    c = {"request": {"a": None}}
    assert evaluate_leaf({"field": "request.a", "operator": "IS_NULL"}, c)
    assert evaluate_leaf({"field": "request.b", "operator": "IS_NULL"}, c)  # missing == null


def test_nested_condition_groups():
    c = {"request": {"a": 1, "b": "x"}, "resource": {"s": "RESTRICTED"}}
    node = {
        "all": [
            {"field": "resource.s", "operator": "EQUALS", "value": "RESTRICTED"},
            {"any": [
                {"field": "request.a", "operator": "EQUALS", "value": 2},
                {"field": "request.b", "operator": "EQUALS", "value": "x"},
            ]},
            {"not": {"field": "request.a", "operator": "EQUALS", "value": 99}},
        ]
    }
    assert evaluate_conditions(node, c)


# ---- engine decisions ----

def _restricted_export_policies():
    return [
        ActivePolicy("p1", "v1", "Restricted access", 20, {
            "applies_to": {"request_type": "DATASET_ACCESS"},
            "conditions": {"all": [
                {"field": "resource.sensitivity", "operator": "EQUALS", "value": "RESTRICTED"}]},
            "actions": [
                {"type": "REQUIRE_APPROVAL", "role": "DATA_OWNER", "stage": 2},
                {"type": "SET_MAXIMUM_DURATION", "days": 7},
                {"type": "ADD_RISK", "name": "restricted", "points": 8},
            ],
        }),
        ActivePolicy("p2", "v2", "Cross region", 15, {
            "applies_to": {"request_type": "DATASET_ACCESS"},
            "conditions": {"all": [
                {"field": "request.requested_action", "operator": "EQUALS", "value": "EXPORT"},
                {"field": "request.destination_region", "operator": "NOT_IN", "value": ["IN", "SG"]}]},
            "actions": [
                {"type": "REQUIRE_APPROVAL", "role": "COMPLIANCE_OFFICER", "stage": 2},
                {"type": "ADD_VIOLATION", "reason": "Restricted export outside approved regions."},
            ],
        }),
    ]


def test_requires_approval_merges_stages():
    context = ctx(request_type="DATASET_ACCESS", requested_action="EXPORT",
                  destination_region="US", duration_days=30,
                  _resource={"sensitivity": "RESTRICTED"})
    d = PolicyEngine().evaluate_request(context, _restricted_export_policies())
    assert d.decision == "REQUIRES_APPROVAL"
    roles = {a.role for a in d.required_approval_stages}
    assert roles == {"DATA_OWNER", "COMPLIANCE_OFFICER"}
    assert d.maximum_duration == 7
    # duration violation auto-added
    assert any("exceeds" in v for v in d.violations)


def test_duplicate_roles_deduped():
    policies = [
        ActivePolicy("a", "a1", "A", 10, {
            "applies_to": {}, "conditions": {},
            "actions": [{"type": "REQUIRE_APPROVAL", "role": "MANAGER", "stage": 1}]}),
        ActivePolicy("b", "b1", "B", 20, {
            "applies_to": {}, "conditions": {},
            "actions": [{"type": "REQUIRE_APPROVAL", "role": "MANAGER", "stage": 1}]}),
    ]
    d = PolicyEngine().evaluate_request(ctx(request_type="X"), policies)
    managers = [a for a in d.required_approval_stages if a.role == "MANAGER" and a.stage == 1]
    assert len(managers) == 1


def test_strictest_duration_wins():
    policies = [
        ActivePolicy("a", "a1", "A", 10, {
            "applies_to": {}, "conditions": {},
            "actions": [{"type": "SET_MAXIMUM_DURATION", "days": 30}]}),
        ActivePolicy("b", "b1", "B", 20, {
            "applies_to": {}, "conditions": {},
            "actions": [{"type": "SET_MAXIMUM_DURATION", "days": 3}]}),
    ]
    d = PolicyEngine().evaluate_request(ctx(request_type="X"), policies)
    assert d.maximum_duration == 3


def test_rejection_overrides_approval():
    policies = [
        ActivePolicy("a", "a1", "Reject", 5, {
            "applies_to": {}, "conditions": {},
            "actions": [{"type": "REJECT", "reason": "Prohibited"}]}),
        ActivePolicy("b", "b1", "Approve", 20, {
            "applies_to": {}, "conditions": {},
            "actions": [{"type": "REQUIRE_APPROVAL", "role": "MANAGER", "stage": 1}]}),
    ]
    d = PolicyEngine().evaluate_request(ctx(request_type="X"), policies)
    assert d.decision == "REJECT"
    assert d.conflicts  # conflict surfaced


def test_auto_approve_when_no_policy_matches():
    d = PolicyEngine().evaluate_request(ctx(request_type="DATASET_ACCESS",
                                            _resource={"sensitivity": "PUBLIC"}),
                                        _restricted_export_policies())
    assert d.decision == "AUTO_APPROVE"
    assert d.required_approval_stages == []
