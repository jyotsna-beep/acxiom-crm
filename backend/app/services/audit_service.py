from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def write_audit(
    db: Session,
    *,
    actor_id: UUID | None,
    action: str,
    entity_name: str,
    record_id: UUID | None,
    result: str = "success",
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    details: str | None = None,
    ip_address: str | None = None,
) -> None:
    """Append a safe, structured audit record within the caller's transaction."""
    db.add(
        AuditLog(
            user_id=actor_id,
            action=action,
            entity_name=entity_name,
            record_id=str(record_id) if record_id else None,
            result=result,
            old_value=old_value,
            new_value=new_value,
            details=details,
            ip_address=ip_address,
        )
    )
