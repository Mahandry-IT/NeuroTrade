"""Entités market_analysis — signaux techniques calculés."""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, Float, String, DateTime, JSON

from app.core.database import Base


class TechnicalSignal(Base):
    """Signal technique calculé par Python pur (RSI, MACD, etc.)."""
    __tablename__ = "technical_signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    rsi = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_histogram = Column(Float, nullable=True)
    sma_short = Column(Float, nullable=True)
    sma_long = Column(Float, nullable=True)
    ema_short = Column(Float, nullable=True)
    ema_long = Column(Float, nullable=True)
    indicators_raw = Column(JSON, nullable=True)  # données brutes supplémentaires
    computed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
