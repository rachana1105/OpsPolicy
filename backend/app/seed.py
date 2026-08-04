"""Seed the Northstar Enterprises demo organisation.

Idempotent-ish: if the organisation already exists, it is left as-is.
Run with:  python -m app.seed
"""
from datetime import datetime, timezone

from app.core.security import hash_password
from app.db.base import Base
from app.db.seed_policies import SEED_POLICIES
from app.db.session import SessionLocal, engine
from app.models.enums import (
    Criticality,
    EmployeeType,
    PolicyStatus,
    PolicyType,
    ResourceType,
    Role,
    Sensitivity,
)
from app.models.org import (
    BusinessUnit,
    Department,
    Organisation,
    Resource,
    Team,
    User,
)
from app.models.policy import Policy, PolicyVersion

DEFAULT_PASSWORD = "opspolicy123"


def seed() -> None:
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        existing = db.query(Organisation).filter(Organisation.name == "Northstar Enterprises").first()
        if existing:
            print("Northstar Enterprises already seeded. Skipping.")
            return

        org = Organisation(name="Northstar Enterprises")
        db.add(org)
        db.flush()

        # Business units
        bu_tech = BusinessUnit(organisation_id=org.id, name="Technology")
        bu_fin = BusinessUnit(organisation_id=org.id, name="Finance")
        bu_ops = BusinessUnit(organisation_id=org.id, name="Operations")
        db.add_all([bu_tech, bu_fin, bu_ops])
        db.flush()

        # Departments
        dep_data = Department(business_unit_id=bu_tech.id, name="Data Platform")
        dep_app = Department(business_unit_id=bu_tech.id, name="Application Engineering")
        dep_sec = Department(business_unit_id=bu_tech.id, name="Information Security")
        dep_comp = Department(business_unit_id=bu_ops.id, name="Compliance")
        dep_proc = Department(business_unit_id=bu_fin.id, name="Procurement")
        dep_vendor = Department(business_unit_id=bu_ops.id, name="Vendor Operations")
        departments = [dep_data, dep_app, dep_sec, dep_comp, dep_proc, dep_vendor]
        db.add_all(departments)
        db.flush()

        # Teams
        team_data = Team(department_id=dep_data.id, name="Data Platform Core")
        team_app = Team(department_id=dep_app.id, name="Platform Engineering")
        team_sec = Team(department_id=dep_sec.id, name="Security Review")
        team_comp = Team(department_id=dep_comp.id, name="Compliance Office")
        team_proc = Team(department_id=dep_proc.id, name="Procurement Desk")
        team_vendor = Team(department_id=dep_vendor.id, name="Vendor Ops")
        teams = [team_data, team_app, team_sec, team_comp, team_proc, team_vendor]
        db.add_all(teams)
        db.flush()

        def mk_user(name, email, role, team, emp=EmployeeType.EMPLOYEE, manager=None):
            u = User(
                organisation_id=org.id, team_id=team.id if team else None,
                manager_id=manager.id if manager else None, employee_type=emp,
                name=name, email=email, role=role,
                password_hash=hash_password(DEFAULT_PASSWORD),
            )
            db.add(u)
            db.flush()
            return u

        # Leadership / reviewers
        admin = mk_user("Aisha Rao", "admin@northstar.io", Role.PLATFORM_ADMIN, team_comp)
        dh_tech = mk_user("Vikram Shah", "vikram.head@northstar.io", Role.DEPARTMENT_HEAD, team_app)
        dh_fin = mk_user("Neha Gupta", "neha.head@northstar.io", Role.DEPARTMENT_HEAD, team_proc)

        mgr_data = mk_user("Priya Menon", "priya.mgr@northstar.io", Role.MANAGER, team_data)
        mgr_app = mk_user("Rohit Nair", "rohit.mgr@northstar.io", Role.MANAGER, team_app)
        mgr_sec = mk_user("Arjun Iyer", "arjun.mgr@northstar.io", Role.MANAGER, team_sec)
        mgr_comp = mk_user("Sara Khan", "sara.mgr@northstar.io", Role.MANAGER, team_comp)
        mgr_proc = mk_user("Deepak Rao", "deepak.mgr@northstar.io", Role.MANAGER, team_proc)
        mgr_vendor = mk_user("Meera Das", "meera.mgr@northstar.io", Role.MANAGER, team_vendor)

        data_owner_1 = mk_user("Kabir Sen", "kabir.owner@northstar.io", Role.DATA_OWNER, team_data)
        data_owner_2 = mk_user("Ananya Roy", "ananya.owner@northstar.io", Role.DATA_OWNER, team_data)
        data_owner_3 = mk_user("Farah Ali", "farah.owner@northstar.io", Role.DATA_OWNER, team_data)

        sec_1 = mk_user("Rahul Verma", "rahul.sec@northstar.io", Role.SECURITY_REVIEWER, team_sec)
        sec_2 = mk_user("Tara Bose", "tara.sec@northstar.io", Role.SECURITY_REVIEWER, team_sec)

        comp_1 = mk_user("Ishaan Malhotra", "ishaan.comp@northstar.io", Role.COMPLIANCE_OFFICER, team_comp)
        comp_2 = mk_user("Divya Pillai", "divya.comp@northstar.io", Role.COMPLIANCE_OFFICER, team_comp)

        fin_1 = mk_user("Nikhil Jain", "nikhil.fin@northstar.io", Role.FINANCE_REVIEWER, team_proc)
        fin_2 = mk_user("Pooja Reddy", "pooja.fin@northstar.io", Role.FINANCE_REVIEWER, team_proc)

        # Employees and contractors (requesters)
        emp_analyst = mk_user("Lena Fernandes", "lena@northstar.io", Role.EMPLOYEE, team_data,
                              manager=mgr_data)
        emp_engineer = mk_user("Omar Sheikh", "omar@northstar.io", Role.EMPLOYEE, team_app,
                               manager=mgr_app)
        contractor = mk_user("Sam Wright", "sam.contractor@northstar.io", Role.EMPLOYEE, team_vendor,
                             emp=EmployeeType.CONTRACTOR, manager=mgr_vendor)
        emp_procure = mk_user("Riya Kapoor", "riya@northstar.io", Role.EMPLOYEE, team_proc,
                              manager=mgr_proc)

        # set department heads
        dep_app.head_user_id = dh_tech.id
        dep_proc.head_user_id = dh_fin.id

        # Resources
        resources = [
            Resource(organisation_id=org.id, name="customer_profiles", resource_type=ResourceType.DATASET,
                     owner_user_id=data_owner_1.id, criticality=Criticality.CRITICAL,
                     sensitivity=Sensitivity.RESTRICTED, region="IN"),
            Resource(organisation_id=org.id, name="transactions_ledger", resource_type=ResourceType.DATASET,
                     owner_user_id=data_owner_2.id, criticality=Criticality.HIGH,
                     sensitivity=Sensitivity.RESTRICTED, region="IN"),
            Resource(organisation_id=org.id, name="marketing_events", resource_type=ResourceType.DATASET,
                     owner_user_id=data_owner_3.id, criticality=Criticality.MEDIUM,
                     sensitivity=Sensitivity.INTERNAL, region="IN"),
            Resource(organisation_id=org.id, name="payments-prod", resource_type=ResourceType.PRODUCTION_SERVICE,
                     owner_user_id=mgr_app.id, criticality=Criticality.CRITICAL,
                     sensitivity=Sensitivity.CONFIDENTIAL, region="IN"),
            Resource(organisation_id=org.id, name="checkout-prod", resource_type=ResourceType.PRODUCTION_SERVICE,
                     owner_user_id=mgr_app.id, criticality=Criticality.HIGH,
                     sensitivity=Sensitivity.CONFIDENTIAL, region="IN"),
            Resource(organisation_id=org.id, name="staging-env", resource_type=ResourceType.ENVIRONMENT,
                     owner_user_id=mgr_app.id, criticality=Criticality.MEDIUM,
                     sensitivity=Sensitivity.INTERNAL, region="IN"),
            Resource(organisation_id=org.id, name="analytics-platform", resource_type=ResourceType.APPLICATION,
                     owner_user_id=mgr_data.id, criticality=Criticality.MEDIUM,
                     sensitivity=Sensitivity.INTERNAL, region="IN"),
            Resource(organisation_id=org.id, name="crm-vendor-contract", resource_type=ResourceType.VENDOR_CONTRACT,
                     owner_user_id=dh_fin.id, criticality=Criticality.LOW,
                     sensitivity=Sensitivity.INTERNAL, region="IN"),
            Resource(organisation_id=org.id, name="hr_records", resource_type=ResourceType.DATASET,
                     owner_user_id=data_owner_1.id, criticality=Criticality.HIGH,
                     sensitivity=Sensitivity.RESTRICTED, region="IN"),
            Resource(organisation_id=org.id, name="logs-prod", resource_type=ResourceType.PRODUCTION_SERVICE,
                     owner_user_id=mgr_app.id, criticality=Criticality.MEDIUM,
                     sensitivity=Sensitivity.INTERNAL, region="IN"),
        ]
        db.add_all(resources)
        db.flush()

        # Policies (published, versioned)
        now = datetime.now(timezone.utc)
        for spec in SEED_POLICIES:
            policy = Policy(
                organisation_id=org.id, name=spec["name"], description=spec["definition"].get("name"),
                policy_type=PolicyType(spec["policy_type"]), priority=spec["priority"],
                status=PolicyStatus.PUBLISHED, version=1, effective_from=now, owner_user_id=comp_1.id,
            )
            db.add(policy)
            db.flush()
            version = PolicyVersion(
                policy_id=policy.id, version_number=1, definition_json=spec["definition"],
                change_summary="Initial seeded version", created_by=comp_1.id,
            )
            db.add(version)
            db.flush()
            policy.published_version_id = version.id

        db.commit()
        print("Seeded Northstar Enterprises.")
        print(f"  Users: {db.query(User).count()}  Resources: {db.query(Resource).count()}  "
              f"Policies: {db.query(Policy).count()}")
        print(f"  Login with any seeded email and password '{DEFAULT_PASSWORD}'.")
        print("  e.g. lena@northstar.io / admin@northstar.io / kabir.owner@northstar.io")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
