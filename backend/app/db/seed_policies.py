"""Seed policy definitions in the structured rule format."""

SEED_POLICIES = [
    {
        "name": "Restricted dataset requires data-owner approval",
        "policy_type": "DATA",
        "priority": 20,
        "definition": {
            "name": "Restricted dataset access",
            "applies_to": {"request_type": "DATASET_ACCESS"},
            "conditions": {
                "all": [
                    {"field": "resource.sensitivity", "operator": "EQUALS", "value": "RESTRICTED"}
                ]
            },
            "actions": [
                {"type": "REQUIRE_APPROVAL", "role": "DATA_OWNER", "stage": 2},
                {"type": "ADD_RISK", "name": "restricted_dataset", "points": 8,
                 "reason": "Restricted dataset access"},
            ],
        },
    },
    {
        "name": "Restricted dataset export outside approved regions requires compliance",
        "policy_type": "DATA",
        "priority": 15,
        "definition": {
            "name": "Cross-region export",
            "applies_to": {"request_type": "DATASET_ACCESS"},
            "conditions": {
                "all": [
                    {"field": "resource.sensitivity", "operator": "EQUALS", "value": "RESTRICTED"},
                    {"field": "request.requested_action", "operator": "EQUALS", "value": "EXPORT"},
                    {"field": "request.destination_region", "operator": "NOT_IN",
                     "value": ["IN", "SG"]},
                ]
            },
            "actions": [
                {"type": "REQUIRE_APPROVAL", "role": "COMPLIANCE_OFFICER", "stage": 2},
                {"type": "ADD_RISK", "name": "cross_region_export", "points": 6,
                 "reason": "Cross-region restricted export"},
                {"type": "ADD_VIOLATION",
                 "reason": "Restricted data cannot be exported outside approved regions without compliance approval."},
            ],
        },
    },
    {
        "name": "Contractor access cannot exceed seven days",
        "policy_type": "ACCESS",
        "priority": 30,
        "definition": {
            "name": "Maximum access duration for contractors",
            "applies_to": {},
            "conditions": {
                "all": [
                    {"field": "requester.employee_type", "operator": "EQUALS", "value": "CONTRACTOR"}
                ]
            },
            "actions": [
                {"type": "SET_MAXIMUM_DURATION", "days": 7},
                {"type": "ADD_RISK", "name": "contractor_access", "points": 3,
                 "reason": "Contractor requester"},
            ],
        },
    },
    {
        "name": "Restricted datasets have a seven-day maximum duration",
        "policy_type": "DATA",
        "priority": 25,
        "definition": {
            "name": "Maximum access duration",
            "applies_to": {"request_type": "DATASET_ACCESS"},
            "conditions": {
                "all": [
                    {"field": "resource.sensitivity", "operator": "EQUALS", "value": "RESTRICTED"}
                ]
            },
            "actions": [{"type": "SET_MAXIMUM_DURATION", "days": 7}],
        },
    },
    {
        "name": "Production admin access requires manager and security approval",
        "policy_type": "SECURITY",
        "priority": 20,
        "definition": {
            "name": "Production admin access",
            "applies_to": {"request_type": "PRODUCTION_ACCESS"},
            "conditions": {
                "all": [
                    {"field": "request.requested_role", "operator": "EQUALS", "value": "ADMIN"}
                ]
            },
            "actions": [
                {"type": "REQUIRE_APPROVAL", "role": "MANAGER", "stage": 1},
                {"type": "REQUIRE_APPROVAL", "role": "SECURITY_REVIEWER", "stage": 2},
                {"type": "ADD_RISK", "name": "production_admin", "points": 6,
                 "reason": "Production admin access"},
            ],
        },
    },
    {
        "name": "Emergency production access expires after two hours",
        "policy_type": "SECURITY",
        "priority": 10,
        "definition": {
            "name": "Emergency production access",
            "applies_to": {"request_type": "PRODUCTION_ACCESS"},
            "conditions": {
                "all": [{"field": "request.emergency", "operator": "EQUALS", "value": True}]
            },
            "actions": [
                {"type": "SET_MAXIMUM_DURATION", "days": 1},
                {"type": "REQUIRE_APPROVAL", "role": "MANAGER", "stage": 1},
                {"type": "REQUIRE_APPROVAL", "role": "SECURITY_REVIEWER", "stage": 1},
                {"type": "ADD_RISK", "name": "emergency_access", "points": 5,
                 "reason": "Emergency production access"},
            ],
        },
    },
    {
        "name": "Purchases above five lakh require finance approval",
        "policy_type": "PROCUREMENT",
        "priority": 30,
        "definition": {
            "name": "Finance approval threshold",
            "applies_to": {"request_type": "PURCHASE_APPROVAL"},
            "conditions": {
                "all": [
                    {"field": "request.amount", "operator": "GREATER_THAN", "value": 500000}
                ]
            },
            "actions": [
                {"type": "REQUIRE_APPROVAL", "role": "FINANCE_REVIEWER", "stage": 1},
                {"type": "ADD_RISK", "name": "high_value_purchase", "points": 3,
                 "reason": "Purchase above five lakh"},
            ],
        },
    },
    {
        "name": "Purchases above ten lakh require finance and department-head approval",
        "policy_type": "PROCUREMENT",
        "priority": 25,
        "definition": {
            "name": "Department-head approval threshold",
            "applies_to": {"request_type": "PURCHASE_APPROVAL"},
            "conditions": {
                "all": [
                    {"field": "request.amount", "operator": "GREATER_THAN", "value": 1000000}
                ]
            },
            "actions": [
                {"type": "REQUIRE_APPROVAL", "role": "FINANCE_REVIEWER", "stage": 1},
                {"type": "REQUIRE_APPROVAL", "role": "DEPARTMENT_HEAD", "stage": 1},
                {"type": "ADD_RISK", "name": "very_high_value_purchase", "points": 4,
                 "reason": "Purchase above ten lakh"},
            ],
        },
    },
]
