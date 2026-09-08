"""Service trading_config — paramètres de trading + contrôle bot (RG-1 à RG-3, RG-8, RG-9)."""

import logging
from datetime import datetime, timezone
from functools import partial

from sqlalchemy.orm import Session

from app.modules.trading_config.repository import TradingConfigRepository, BotStateRepository
from app.modules.trading_config.models import BotStatus
from app.modules.auth.service import AuthService
from app.core.scheduler import start_scheduler, stop_scheduler, is_running

logger = logging.getLogger(__name__)


class TradingConfigService:
    def __init__(self, db: Session):
        self.config_repo = TradingConfigRepository(db)
        self.bot_repo = BotStateRepository(db)
        self.auth_service = AuthService(db)
        self.db = db

    def get_config(self, user_id: int) -> dict:
        config = self.config_repo.get_or_create(user_id)
        return {
            "id": config.id,
            "user_id": config.user_id,
            "gain_limit_pct": config.gain_limit_pct,
            "loss_limit_pct": config.loss_limit_pct,
            "capital_pct_per_trade": config.capital_pct_per_trade,
            "max_trades_per_month": config.max_trades_per_month,
            "min_holding_duration": config.min_holding_duration,
            "tax_alert_threshold": config.tax_alert_threshold,
            "simulation_mode": config.simulation_mode,
            "kraken_pair": config.kraken_pair,
            "auto_discover_markets": config.auto_discover_markets,
            "max_concurrent_positions": config.max_concurrent_positions,
            "quote_currency": config.quote_currency,
            "min_volume_24h": config.min_volume_24h,
            "scanner_cache_ttl": config.scanner_cache_ttl,
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }

    def update_config(self, user_id: int, **kwargs) -> dict:
        # Crée la config si elle n'existe pas encore
        self.config_repo.get_or_create(user_id)
        config = self.config_repo.update(user_id, **kwargs)
        if not config:
            raise ValueError("Config not found")
        logger.info("config_updated user_id=%d fields=%s", user_id, list(kwargs.keys()))
        return self.get_config(user_id)

    def set_simulation_mode(self, user_id: int, simulation_mode: bool, confirm: bool) -> str:
        """RG-5 : confirmation explicite non réversible requise."""
        if not confirm:
            raise ValueError("Confirmation required to change simulation mode")
        config = self.config_repo.update(user_id, simulation_mode=simulation_mode)
        mode_label = "simulation" if simulation_mode else "REAL"
        logger.info("simulation_mode_changed user_id=%d mode=%s", user_id, mode_label)
        return mode_label

    def start_bot(self, user_id: int, analysis_callback) -> dict:
        """Démarre le bot — vérifie connexion plateforme (RG-6)."""
        logger.info("start_bot.step1_check_platform user_id=%d", user_id)
        if not self.auth_service.is_platform_connected(user_id):
            raise ValueError("Platform not connected — cannot start bot")

        logger.info("start_bot.step2_set_running user_id=%d", user_id)
        bot_state = self.bot_repo.set_running(user_id)

        logger.info("start_bot.step3_start_scheduler user_id=%d callback=%s", user_id, type(analysis_callback).__name__)
        # Bind user_id so APScheduler can call the callback without arguments
        bound_callback = partial(analysis_callback, user_id)
        start_scheduler(bound_callback, interval_seconds=60)

        logger.info("bot_started user_id=%d", user_id)
        return {"status": "running", "message": "Bot started successfully"}

    def stop_bot(self, user_id: int) -> dict:
        """Arrêt immédiat du bot (RG-6)."""
        bot_state = self.bot_repo.set_stopped(user_id)
        stop_scheduler()
        logger.info("bot_stopped user_id=%d", user_id)
        return {"status": "stopped", "message": "Bot stopped immediately"}

    def get_bot_status(self, user_id: int) -> dict:
        state = self.bot_repo.get_or_create(user_id)
        return {
            "status": state.status.value,
            "last_cycle_at": state.last_cycle_at,
            "started_at": state.started_at,
        }
