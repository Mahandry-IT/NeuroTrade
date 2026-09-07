"""Repository tax_tracking — compteurs fiscaux + export (RG-8, RG-11)."""

from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.modules.tax_tracking.models import TaxableConversion
from app.modules.trading_engine.models import Trade, TradeType


class TaxTrackingRepository:
    def __init__(self, db: Session):
        self.db = db

    def record_conversion(
        self, user_id: int, trade_id: int, amount_fiat: float
    ) -> TaxableConversion:
        conv = TaxableConversion(
            user_id=user_id, trade_id=trade_id, amount_fiat=amount_fiat
        )
        self.db.add(conv)
        self.db.commit()
        self.db.refresh(conv)
        return conv

    def get_yearly_fiat_volume(self, user_id: int) -> float:
        """RG-11 : volume fiat converti depuis le 1er janvier."""
        now = datetime.now(timezone.utc)
        start_of_year = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        result = (
            self.db.query(func.coalesce(func.sum(TaxableConversion.amount_fiat), 0.0))
            .filter(
                TaxableConversion.user_id == user_id,
                TaxableConversion.converted_at >= start_of_year,
            )
            .scalar()
        )
        return float(result)

    def get_monthly_trade_count(self, user_id: int) -> int:
        """RG-8 : nombre de trades ce mois."""
        now = datetime.now(timezone.utc)
        start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return (
            self.db.query(func.count(Trade.id))
            .filter(
                Trade.user_id == user_id,
                Trade.trade_type == TradeType.SELL,
                Trade.executed_at >= start_of_month,
                Trade.is_simulated == True,  # compte les trades simulés
            )
            .scalar()
        )

    def get_export_data(
        self,
        user_id: int,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> List[Trade]:
        """Données pour l'export CSV (RG-11)."""
        query = (
            self.db.query(Trade)
            .filter(Trade.user_id == user_id, Trade.trade_type == TradeType.SELL)
        )
        if date_from:
            query = query.filter(Trade.executed_at >= date_from)
        if date_to:
            query = query.filter(Trade.executed_at <= date_to)
        return query.order_by(Trade.executed_at.desc()).all()
