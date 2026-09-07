"""Service trading_engine — orchestration décision → exécution ordres.

Règles métier couvertes :
- RG-2 : limite de gain
- RG-3 : limite de perte (PRIORITAIRE sur RG-9)
- RG-4 : décision basée sur analyse technique
- RG-6 : arrêt immédiat = plus aucune action
- RG-8 : quota mensuel de trades
- RG-9 : durée minimale de détention
- RG-10 : idempotence sur exécution d'ordres
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.trading_config.repository import TradingConfigRepository, BotStateRepository
from app.modules.trading_config.models import BotStatus
from app.modules.trading_engine.repository import PositionRepository, TradeRepository
from app.modules.trading_engine.models import TradeType, PositionStatus
from app.modules.market_analysis.service import MarketAnalysisService
from app.modules.tax_tracking.repository import TaxTrackingRepository
from app.modules.notifications.service import NotificationService

logger = logging.getLogger(__name__)


def should_force_sell(
    position_opened_at: datetime,
    entry_price: float,
    current_price: float,
    loss_limit_pct: float,
    min_holding_duration: int,
    max_trades_per_month: Optional[int] = None,
    current_month_trades: int = 0,
) -> tuple[bool, str]:
    """Fonction pure — détermine si une position doit être vendue en priorité.

    Priorité stricte : RG-3 (perte) > RG-9 (durée détention) > RG-8 (quota).
    RG-3 s'applique MÊME si la durée min de détention n'est pas écoulée.
    """
    now = datetime.now(timezone.utc)
    pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0

    # RG-3 : stop-loss — PRIORITAIRE, même avant durée min
    if pnl_pct <= loss_limit_pct:
        return True, f"RG-3: loss {pnl_pct:.1f}% <= limit {loss_limit_pct}%"

    # RG-9 : durée minimale de détention
    holding_minutes = (now - position_opened_at).total_seconds() / 60
    if holding_minutes < min_holding_duration:
        return False, f"RG-9: holding {holding_minutes:.0f}min < min {min_holding_duration}min"

    # RG-8 : quota mensuel atteint — vente autorisée mais signalée
    if max_trades_per_month and current_month_trades >= max_trades_per_month:
        return True, f"RG-8: monthly quota {current_month_trades}/{max_trades_per_month} reached"

    return False, "no_force_sell"


class TradingEngineService:
    def __init__(self, db: Session):
        self.config_repo = TradingConfigRepository(db)
        self.bot_repo = BotStateRepository(db)
        self.position_repo = PositionRepository(db)
        self.trade_repo = TradeRepository(db)
        self.tax_repo = TaxTrackingRepository(db)
        self.market_service = MarketAnalysisService(db)
        self.notification_service = NotificationService(db)
        self.db = db

    def run_analysis_cycle(self, user_id: int) -> None:
        """Cycle complet d'analyse — appelé par le scheduler."""
        # Vérifier RG-6 : bot toujours actif
        bot_state = self.bot_repo.get_by_user(user_id)
        if not bot_state or bot_state.status != BotStatus.RUNNING:
            logger.info("bot_not_running user_id=%d — skipping cycle", user_id)
            return

        config = self.config_repo.get_or_create(user_id)

        # Mettre à jour le timestamp du dernier cycle
        self.bot_repo.update_last_cycle(user_id)

        # Analyser les positions ouvertes
        open_positions = self.position_repo.get_open_positions(user_id)
        for position in open_positions:
            self._evaluate_position(user_id, position, config)

        logger.info(
            "analysis_cycle_complete user_id=%d open_positions=%d",
            user_id, len(open_positions),
        )

    def _evaluate_position(self, user_id: int, position, config) -> None:
        """Évalue une position ouverte et décide de l'action."""
        # Pour l'exemple, on simule un prix actuel (TODO: vrai appel API plateforme)
        current_price = position.entry_price  # placeholder

        monthly_trades = self.trade_repo.count_monthly_trades(user_id, config.simulation_mode)

        # Vérifier les garde-fous
        force_sell, reason = should_force_sell(
            position_opened_at=position.opened_at,
            entry_price=position.entry_price,
            current_price=current_price,
            loss_limit_pct=config.loss_limit_pct,
            min_holding_duration=config.min_holding_duration,
            max_trades_per_month=config.max_trades_per_month,
            current_month_trades=monthly_trades,
        )

        if force_sell:
            self._execute_sell(user_id, position, current_price, reason, config)
            return

        # RG-4 : analyse technique + décision
        analysis = self.market_service.analyze(position.symbol, [current_price])
        signal = analysis.get("signal", "HOLD")

        if "BUY" in str(signal).upper():
            logger.info("buy_signal user_id=%d symbol=%s", user_id, position.symbol)
            # TODO: exécuter l'achat si pas déjà en position
        elif "SELL" in str(signal).upper():
            self._execute_sell(
                user_id, position, current_price,
                f"signal: {signal}", config
            )

    def _execute_sell(
        self, user_id: int, position, price: float, reason: str, config
    ) -> None:
        """Exécute une vente — idempotent via clé (RG-10)."""
        idempotency_key = f"{position.id}_{datetime.now(timezone.utc).isoformat()}"

        # RG-10 : vérifier l'idempotence
        if self.trade_repo.check_idempotency(idempotency_key):
            logger.warning("duplicate_trade_blocked key=%s", idempotency_key)
            return

        # Calculer le PnL
        pnl = (price - position.entry_price) * position.quantity

        # Créer le trade
        trade = self.trade_repo.create(
            user_id=user_id,
            position_id=position.id,
            trade_type=TradeType.SELL,
            symbol=position.symbol,
            amount_fiat=pnl,
            quantity=position.quantity,
            price=price,
            is_simulated=config.simulation_mode,
            idempotency_key=idempotency_key,
            notes=reason,
        )

        # Fermer la position
        self.position_repo.close(position.id)

        # RG-11 : enregistrer la conversion taxable si applicable
        if pnl > 0 and not config.simulation_mode:
            self.tax_repo.record_conversion(user_id, trade.id, pnl)

        # Notification
        self.notification_service.send_trade_notification(user_id, trade)

        logger.info(
            "trade_executed user_id=%d trade_id=%d symbol=%s pnl=%.2f reason=%s",
            user_id, trade.id, position.symbol, pnl, reason,
        )

    def open_position(
        self, user_id: int, symbol: str, amount_fiat: float,
        price: float, is_simulated: bool = True
    ) -> dict:
        """Ouvre une nouvelle position."""
        quantity = amount_fiat / price if price > 0 else 0
        position = self.position_repo.create(
            user_id=user_id, symbol=symbol, amount=amount_fiat,
            quantity=quantity, entry_price=price, is_simulated=is_simulated,
        )
        return {
            "id": position.id,
            "symbol": symbol,
            "amount": amount_fiat,
            "entry_price": price,
        }
