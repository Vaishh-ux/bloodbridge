from typing import Optional

from fastapi import Request
from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog


def audit(db: Session, user_id: Optional[int], action: str, entity: str = None, entity_id: int = None,
          details: str = None, request: Optional[Request] = None) -> None:
    """Add an audit record to the current transaction (caller commits). Never log secrets."""
    ip = request.client.host if request is not None and request.client else None
    db.add(AuditLog(user_id=user_id, action=action, entity=entity, entity_id=entity_id, details=details, ip_address=ip))
