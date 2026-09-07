"""Entités trading_engine — Position + Trade."""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, Float, String, DateTime, Enum, Boolean, ForeignKey, Text, Index
)

from app.core.database import Base


class PositionStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"


class TradeType(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"


class OrderResult(str, enum.Enum):
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    FAILED = "failed"
    SIMULATED = "simulated"


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    amount = Column(Float, nullable=False)  # montant investi en fiat
    quantity = Column(Float, nullable=False)  # quantité de crypto
    entry_price = Column(Float, nullable=False)
    opened_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    closed_at = Column(DateTime(timezone=True), nullable=True)
    status = Column(Enum(PositionStatus), default=PositionStatus.OPEN, nullable=False)
    is_simulated = Column(Boolean, default=True, nullable=False)

    __table_args__ = (
        Index("idx_positions_status", "status"),
        Index("idx_positions_user_status", "user_id", "status"),
    )


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True, autoincrement=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    trade_type = Column(Enum(TradeType), nullable=False)
    symbol = Column(String(20), nullable=False)
    amount_fiat = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)
    executed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    result = Column(Enum(OrderResult), default=OrderResult.FILLED)
    is_simulated = Column(Boolean, default=True, nullable=False)
    idempotency_key = Column(String(255), unique=True, nullable=True)  # position_id + cycle_timestamp
    notes = Column(Text, nullable=True)  # raison de la décision (RG-2/3/9 etc.)

    __table_args__ = (
        Index("idx_trades_date", "executed_at"),
        Index("idx_trades_simulated", "is_simulated"),
        Index("idx_trades_user_date", "user_id", "executed_at"),
        Index("idx_trades_idempotency", "idempotency_key"),
    )
