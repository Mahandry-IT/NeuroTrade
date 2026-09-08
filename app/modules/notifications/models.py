"""Entités notifications — Notification (in-app + email)."""

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean, Text, ForeignKey

from app.core.database import Base


class NotificationType(str, enum.Enum):
    TRADE_EXECUTED = "trade_executed"
    LOSS_LIMIT_REACHED = "loss_limit_reached"
    GAIN_LIMIT_REACHED = "gain_limit_reached"
    MONTHLY_QUOTA_REACHED = "monthly_quota_reached"
    TAX_ALERT = "tax_alert"
    BOT_STOPPED = "bot_stopped"
    BOT_STARTED = "bot_started"
    PLATFORM_DISCONNECTED = "platform_disconnected"
    GEMINI_FALLBACK = "gemini_fallback"


class NotificationChannel(str, enum.Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    BOTH = "both"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(Enum(NotificationType, values_callable=lambda e: [x.value for x in e]), nullable=False)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    channel = Column(Enum(NotificationChannel, values_callable=lambda e: [x.value for x in e]), default=NotificationChannel.IN_APP)
    sent = Column(Boolean, default=False)
    read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
