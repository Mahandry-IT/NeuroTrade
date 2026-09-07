"""Router notifications — in-app notifications."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.modules.notifications.service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/")
def get_unread(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = NotificationService(db)
    notifs = service.get_unread(user_id)
    return [
        {
            "id": n.id,
            "type": n.type.value,
            "title": n.title,
            "message": n.message,
            "channel": n.channel.value,
            "created_at": n.created_at,
        }
        for n in notifs
    ]


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(
    notification_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = NotificationService(db)
    service.mark_read(user_id, notification_id)


@router.post("/read-all")
def mark_all_read(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    service = NotificationService(db)
    count = service.mark_all_read(user_id)
    return {"marked_read": count}
