from sqlalchemy.orm import Session as OrmSession

from app.core.domain import uid
from app.models.entities import AuditEvent


def record_audit(
    db: OrmSession,
    action: str,
    *,
    case_id: str | None = None,
    correlation_id: str | None = None,
    metadata: dict | None = None,
    actor: str = "api",
) -> AuditEvent:
    event = AuditEvent(
        id=uid(),
        case_id=case_id,
        correlation_id=correlation_id,
        action=action,
        actor=actor,
        metadata_json=metadata or {},
    )
    db.add(event)
    return event
