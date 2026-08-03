"""Append-only audit event recording and timeline retrieval."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.lifecycle import AuditEvent


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def record(
        self,
        *,
        event_type: str,
        entity_type: str,
        entity_id: str | None = None,
        organisation_id: str | None = None,
        request_id: str | None = None,
        actor_id: str | None = None,
        previous_state: str | None = None,
        new_state: str | None = None,
        payload: dict | None = None,
        request_id_header: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            organisation_id=organisation_id,
            request_id=request_id,
            actor_id=actor_id,
            previous_state=previous_state,
            new_state=new_state,
            payload=payload or {},
            request_id_header=request_id_header,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def timeline(self, request_id: str) -> list[AuditEvent]:
        stmt = (
            select(AuditEvent)
            .where(AuditEvent.request_id == request_id)
            .order_by(AuditEvent.created_at.asc())
        )
        return list(self.db.execute(stmt).scalars().all())

    def search(
        self,
        *,
        organisation_id: str,
        request_id: str | None = None,
        actor_id: str | None = None,
        event_type: str | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        created_from=None,
        created_to=None,
        limit: int = 200,
    ) -> list[AuditEvent]:
        stmt = select(AuditEvent).where(AuditEvent.organisation_id == organisation_id)
        if request_id:
            stmt = stmt.where(AuditEvent.request_id == request_id)
        if actor_id:
            stmt = stmt.where(AuditEvent.actor_id == actor_id)
        if event_type:
            stmt = stmt.where(AuditEvent.event_type == event_type)
        if entity_type:
            stmt = stmt.where(AuditEvent.entity_type == entity_type)
        if entity_id:
            stmt = stmt.where(AuditEvent.entity_id == entity_id)
        if created_from:
            stmt = stmt.where(AuditEvent.created_at >= created_from)
        if created_to:
            stmt = stmt.where(AuditEvent.created_at <= created_to)
        stmt = stmt.order_by(AuditEvent.created_at.desc()).limit(limit)
        return list(self.db.execute(stmt).scalars().all())
