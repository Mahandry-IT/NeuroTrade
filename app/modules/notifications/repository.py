"""Repository notifications — accès données Notification."""

from typing import List

from sqlalchemy.orm import Session

from app.modules.notifications.models import Notification, NotificationType, NotificationChannel


class NotificationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: int,
        type: NotificationType,
        title: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.IN_APP,
    ) -> Notification:
        notif = Notification(
            user_id=user_id, type=type, title=title,
            message=message, channel=channel,
        )
        self.db.add(notif)
        self.db.commit()
        self.db.refresh(notif)
        return notif

    def get_unread(self, user_id: int) -> List[Notification]:
        return (
            self.db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.read == False)
            .order_by(Notification.created_at.desc())
            .all()
        )

    def mark_read(self, user_id: int, notification_id: int) -> None:
        notif = (
            self.db.query(Notification)
            .filter(Notification.id == notification_id, Notification.user_id == user_id)
            .first()
        )
        if notif:
            notif.read = True
            self.db.commit()

    def mark_all_read(self, user_id: int) -> int:
        count = (
            self.db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.read == False)
            .update({"read": True})
        )
        self.db.commit()
        return count
