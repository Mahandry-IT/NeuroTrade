"""Service history — listing chronologique + stats performance (Epic historique)."""

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.trading_engine.repository import TradeRepository
from app.modules.trading_engine.models import TradeType


class HistoryService:
    def __init__(self, db: Session):
        self.trade_repo = TradeRepository(db)

    def get_trades(
        self,
        user_id: int,
        page: int = 1,
        limit: int = 20,
        is_simulated: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        symbol: Optional[str] = None,
    ) -> dict:
        trades, total = self.trade_repo.paginated(
            user_id, page, limit, is_simulated, date_from, date_to, symbol
        )
        return {
            "data": [
                {
                    "id": t.id,
                    "position_id": t.position_id,
                    "trade_type": t.trade_type.value,
                    "symbol": t.symbol,
                    "amount_fiat": t.amount_fiat,
                    "fee": t.fee,
                    "quantity": t.quantity,
                    "price": t.price,
                    "executed_at": t.executed_at,
                    "result": t.result.value,
                    "is_simulated": t.is_simulated,
                    "notes": t.notes,
                }
                for t in trades
            ],
            "meta": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": max(1, -(-total // limit)),  # ceil division
            },
        }

    def get_stats(
        self,
        user_id: int,
        is_simulated: Optional[bool] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> dict:
        stats = self.trade_repo.get_stats(user_id, is_simulated, date_from, date_to)
        return {
            **stats,
            "period_from": date_from,
            "period_to": date_to,
        }
