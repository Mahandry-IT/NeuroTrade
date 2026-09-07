"""Service notifications — in-app + email (Epic notifications)."""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.notifications.repository import NotificationRepository
from app.modules.notifications.models import NotificationType, NotificationChannel
from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, db: Session):
        self.repo = NotificationRepository(db)

    def send_trade_notification(self, user_id: int, trade) -> None:
        """Notifie l'exécution d'un trade."""
        pnl = trade.amount_fiat
        title = f"Trade {trade.trade_type.value} — {trade.symbol}"
        message = (
            f"{'📈' if pnl > 0 else '📉'} {trade.trade_type.value.upper()} {trade.symbol}\n"
            f"Montant: {trade.amount_fiat:.2f} USDT | Prix: {trade.price:.2f}\n"
            f"PnL: {'+' if pnl > 0 else ''}{pnl:.2f}"
        )
        ntype = NotificationType.TRADE_EXECUTED if pnl >= 0 else NotificationType.LOSS_LIMIT_REACHED
        self.repo.create(user_id, ntype, title, message)

    def send_alert(
        self, user_id: int, ntype: NotificationType, title: str, message: str,
        channel: NotificationChannel = NotificationChannel.BOTH
    ) -> None:
        notif = self.repo.create(user_id, ntype, title, message, channel)
        # Envoyer email si configuré
        if channel in (NotificationChannel.EMAIL, NotificationChannel.BOTH):
            self._send_email(user_id, title, message)

    def get_unread(self, user_id: int) -> list:
        return self.repo.get_unread(user_id)

    def mark_read(self, user_id: int, notification_id: int) -> None:
        self.repo.mark_read(user_id, notification_id)

    def mark_all_read(self, user_id: int) -> int:
        return self.repo.mark_all_read(user_id)

    def _send_email(self, user_id: int, subject: str, body: str) -> None:
        """Envoie un email — TODO: implémenter avec SMTP."""
        if not settings.smtp_host:
            logger.debug("smtp_not_configured — skipping email")
            return
        # TODO: implémentation SMTP réelle
        logger.info("email_sent user_id=%d subject=%s", user_id, subject)
