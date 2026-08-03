"""Request orchestration service.

Owns the request lifecycle for Milestone 3: create a draft, submit it (which
runs the deterministic engine, scores risk, persists evaluations, sets the
decision, and either auto-approves or generates the approval workflow), plus
cancel and timeline. All transitions go through the state validator and every
meaningful step writes an audit event.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.service import AuditService
from app.core.errors import ForbiddenError, NotFoundError, ValidationError
from app.db.base import utcnow
from app.models.enums import Decision, RequestStatus, RequestType, RiskLevel, WorkflowStatus
from app.models.org import Resource, User
from app.models.request import (
    ApprovalWorkflow,
    PolicyEvaluation,
    Request,
)
from app.policy_engine import PolicyEngine
from app.policy_engine.context_builder import build_context, load_active_policies
from app.risk_engine import RiskEngine
from app.workflow.builder import build_workflow
from app.workflow.transitions import assert_transition


class RequestService:
    def __init__(self, db: Session, request_id_header: str | None = None):
        self.db = db
        self.audit = AuditService(db)
        self.request_id_header = request_id_header

    # ---- creation ----

    def create_draft(
        self,
        *,
        requester: User,
        request_type: RequestType,
        title: str,
        resource_id: str | None,
        business_justification: str | None,
        payload: dict,
    ) -> Request:
        if request_type != RequestType.PURCHASE_APPROVAL and not resource_id:
            raise ValidationError("A resource is required for this request type.")
        if resource_id:
            resource = self.db.get(Resource, resource_id)
            if not resource or resource.organisation_id != requester.organisation_id:
                raise NotFoundError("Resource not found.")

        req = Request(
            organisation_id=requester.organisation_id,
            request_type=request_type,
            requester_id=requester.id,
            resource_id=resource_id,
            title=title,
            business_justification=business_justification,
            request_payload=payload,
            status=RequestStatus.DRAFT,
        )
        self.db.add(req)
        self.db.flush()
        self.audit.record(
            event_type="REQUEST_CREATED", entity_type="request", entity_id=req.id,
            organisation_id=req.organisation_id, request_id=req.id, actor_id=requester.id,
            new_state=RequestStatus.DRAFT.value, request_id_header=self.request_id_header,
        )
        return req

    # ---- submission (the core Milestone 3 flow) ----

    def submit(self, *, req: Request, actor: User) -> Request:
        # TODO: transition DRAFT -> SUBMITTED -> EVALUATING; build the request
        # context and run it through PolicyEngine.evaluate_request and
        # RiskEngine.score; persist a PolicyEvaluation row per matched policy;
        # record risk_score/risk_level/decision on the request; audit the
        # policy evaluation and risk calculation; then branch on the decision:
        # REJECT -> REJECTED, AUTO_APPROVE -> APPROVED, otherwise build an
        # approval workflow and move to UNDER_REVIEW.
        raise NotImplementedError

    # ---- cancel ----

    def cancel(self, *, req: Request, actor: User) -> Request:
        if req.requester_id != actor.id:
            raise ForbiddenError("Only the requester can cancel this request.")
        assert_transition(req.status, RequestStatus.CANCELLED)
        previous = req.status
        req.status = RequestStatus.CANCELLED
        req.completed_at = utcnow()
        # cancel any active workflow
        wf = self.db.execute(
            select(ApprovalWorkflow).where(ApprovalWorkflow.request_id == req.id)
        ).scalar_one_or_none()
        if wf and wf.status == WorkflowStatus.IN_PROGRESS:
            wf.status = WorkflowStatus.CANCELLED
        self.audit.record(
            event_type="REQUEST_CANCELLED", entity_type="request", entity_id=req.id,
            organisation_id=req.organisation_id, request_id=req.id, actor_id=actor.id,
            previous_state=previous.value, new_state=RequestStatus.CANCELLED.value,
            request_id_header=self.request_id_header,
        )
        req.lock_version += 1
        self.db.flush()
        return req
