"""Repository trading_engine — accès données Position + Trade."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.trading_engine.models import Position, Trade, PositionStatus, TradeType


class PositionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_open_positions(self, user_id: int) -> List[Position]:
        return (
            self.db.query(Position)
            .filter(Position.user_id == user_id, Position.status == PositionStatus.OPEN)
            .all()
        )

    def get_by_id(self, position_id: int) -> Optional[Position]:
        return self.db.query(Position).filter(Position.id == position_id).first()

    def create(
        self, user_id: int, symbol: str, amount: float, quantity: float,
        entry_price: float, is_simulated: bool = True
    ) -> Position:
        pos = Position(
            user_id=user_id, symbol=symbol, amount=amount,
            quantity=quantity, entry_price=entry_price, is_simulated=is_simulated,
        )
        self.db.add(pos)
        self.db.commit()
        self.db.refresh(pos)
        return pos

    def close(self, position_id: int) -> Optional[Position]:
        pos = self.get_by_id(position_id)
        if pos:
            pos.status = PositionStatus.CLOSED
            pos.closed_at = datetime.now(timezone.utc)
            self.db.commit()
            self.db.refresh(pos)
        return pos


class TradeRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        user_id: int,
        position_id: int,
        trade_type: TradeType,
        symbol: str,
        amount_fiat: float,
        quantity: float,
        price: float,
        is_simulated: bool = True,
        idempotency_key: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> Trade:
        trade = Trade(
            user_id=user_id,
            position_id=position_id,
            trade_type=trade_type,
            symbol=symbol,
            amount_fiat=amount_fiat,
            quantity=quantity,
            price=price,
            is_simulated=is_simulated,
            idempotency_key=idempotency_key,
            notes=notes,
        )
        self.db.add(trade)
        self.db.commit()
        self.db.refresh(trade)
        return trade

    def check_idempotency(self, idempotency_key: str) -> bool:
        """Retourne True si le trade existe déjà (clé d'idempotence)."""
        return (
            self.db.query(Trade)
            .filter(Trade.idempotency_key == idempotency_key)
            .first()
            is not None
        )

    def count_monthly_trades(self, user_id: int, is_simulated: bool = True) -> int:
        """Compte les trades du mois en cours (RG-8)."""
        now = datetime.now(timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return (
            self.db.query(func.count(Trade.id))
            .filter(
                Trade.user_id == user_id,
                Trade.executed_at >= start_of_month,
                Trade.is_simulated == is_simulated,
            )
            .scalar()
        )

    def paginated(
        self,
        user_id: int,
        page: int = 1,
        limit: int = 20,
        is_simulated: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        symbol: Optional[str] = None,
    ) -> tuple[List[Trade], int]:
        query = self.db.query(Trade).filter(Trade.user_id == user_id)

        if is_simulated is not None:
            query = query.filter(Trade.is_simulated == is_simulated)
        if date_from:
            query = query.filter(Trade.executed_at >= date_from)
        if date_to:
            query = query.filter(Trade.executed_at <= date_to)
        if symbol:
            query = query.filter(Trade.symbol == symbol)

        total = query.count()
        trades = (
            query.order_by(Trade.executed_at.desc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        return trades, total

    def get_stats(
        self,
        user_id: int,
        is_simulated: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> dict:
        """Stats agrégées : gain cumulé, taux réussite, etc."""
        query = self.db.query(Trade).filter(
            Trade.user_id == user_id,
            Trade.trade_type == TradeType.SELL,
        )
        if is_simulated is not None:
            query = query.filter(Trade.is_simulated == is_simulated)
        if date_from:
            query = query.filter(Trade.executed_at >= date_from)
        if date_to:
            query = query.filter(Trade.executed_at <= date_to)

        trades = query.all()
        total = len(trades)
        winning = sum(1 for t in trades if t.amount_fiat > 0)
        losing = total - winning
        total_gain = sum(t.amount_fiat for t in trades if t.amount_fiat > 0)
        total_loss = sum(t.amount_fiat for t in trades if t.amount_fiat < 0)

        return {
            "total_trades": total,
            "winning_trades": winning,
            "losing_trades": losing,
            "win_rate_pct": round((winning / total * 100) if total > 0 else 0, 2),
            "total_gain_fiat": round(total_gain, 2),
            "total_loss_fiat": round(total_loss, 2),
            "net_pnl_fiat": round(total_gain + total_loss, 2),
        }
