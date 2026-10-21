import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.services.websocket import manager

logger = logging.getLogger("bloodbridge.notifications")


def _payload(n: Notification) -> dict:
    return {
        "id": n.id, "user_id": n.user_id, "request_id": n.request_id, "title": n.title,
        "message": n.message, "type": n.type, "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


async def create_notification(db: Session, user_id: int, title: str, message: str,
                              notification_type: str = "INFO", request_id: Optional[int] = None) -> Notification:
    """Store an in-app notification and push it over WebSocket if the user is online.

    Email/SMS delivery is not configured; integrate a provider here if needed.
    """
    notif = Notification(user_id=user_id, request_id=request_id, title=title, message=message,
                         type=notification_type, is_read=False)
    db.add(notif)
    db.commit()
    db.refresh(notif)
    await manager.send_personal_message({"event": "NOTIFICATION_NEW", "data": _payload(notif)}, user_id)
    return notif


async def push_event(user_id: Optional[int], event: str, data: dict) -> None:
    if user_id:
        await manager.send_personal_message({"event": event, "data": data}, user_id)
