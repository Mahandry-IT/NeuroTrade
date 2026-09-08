"""Entités trading_config — TradingConfig + BotState."""

import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, Float, String, DateTime, Enum, Boolean, ForeignKey

from app.core.database import Base


class BotStatus(str, enum.Enum):
    RUNNING = "running"
    STOPPED = "stopped"


class TradingConfig(Base):
    __tablename__ = "trading_config"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)

    # RG-2 : limite de gain
    gain_limit_pct = Column(Float, default=5.0, nullable=False)
    # RG-3 : limite de perte (prioritaire sur RG-9)
    loss_limit_pct = Column(Float, default=-3.0, nullable=False)
    # Capital investi par trade (% du portefeuille)
    capital_pct_per_trade = Column(Float, default=2.0, nullable=False)
    # RG-8 : quota mensuel de trades
    max_trades_per_month = Column(Integer, default=20, nullable=False)
    # RG-9 : durée minimale de détention (minutes)
    min_holding_duration = Column(Integer, default=60, nullable=False)
    # Seuil d'alerte fiscale (montant fiat cumulé)
    tax_alert_threshold = Column(Float, default=305.0, nullable=False)

    # RG-5 : mode simulation (activé par défaut)
    simulation_mode = Column(Boolean, default=True, nullable=False)

    # Paire de trading Kraken (ex: XXBTZUSD) — utilisé en mode fixed
    kraken_pair = Column(String(20), default="XXBTZUSD", nullable=False)

    # ── Market Scanner — découverte automatique des marchés ──
    auto_discover_markets = Column(Boolean, default=False, nullable=False)
    max_concurrent_positions = Column(Integer, default=3, nullable=False)
    quote_currency = Column(String(10), default="USD", nullable=False)
    min_volume_24h = Column(Float, default=10_000.0, nullable=False)
    scanner_cache_ttl = Column(Integer, default=300, nullable=False)  # secondes

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class BotState(Base):
    __tablename__ = "bot_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    status = Column(Enum(BotStatus, values_callable=lambda e: [x.value for x in e]), default=BotStatus.STOPPED, nullable=False)
    last_cycle_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    stopped_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
