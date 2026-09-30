import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.models.domain import AuditEvent
from app.database.db import (
    save_audit_event, get_audit_events_by_dispute_id, get_audit_events_for_organization
)

class AuditService:
    @staticmethod
    def log_event(
        event_type: str,
        description: str,
        metadata: Dict[str, Any] = None,
        *,
        organization_id: str,
        actor_user_id: Optional[str] = None,
        dispute_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> AuditEvent:
        """
        Logs a persistent audit event into the database.

        organization_id scopes the event to its tenant. actor_user_id is the authenticated
        user who caused the event (None only for system-initiated events such as seeding).
        """
        if dispute_id and not resource_type:
            resource_type, resource_id = "DISPUTE", dispute_id
        event = AuditEvent(
            event_id=f"AUD-{uuid.uuid4().hex[:8].upper()}",
            dispute_id=dispute_id,
            event_type=event_type,
            description=description,
            metadata=metadata or {},
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        save_audit_event(event)
        return event

    @staticmethod
    def get_audit_trail(dispute_id: str, *, organization_id: str) -> List[AuditEvent]:
        """Retrieves chronological audit events for a dispute."""
        return get_audit_events_by_dispute_id(dispute_id, organization_id=organization_id)

    @staticmethod
    def get_organization_activity(*, organization_id: str, limit: int = 50) -> List[AuditEvent]:
        """Most recent audit events across the organization (newest first)."""
        return get_audit_events_for_organization(organization_id=organization_id, limit=limit)
