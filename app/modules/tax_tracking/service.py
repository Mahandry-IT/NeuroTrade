"""Service tax_tracking — compteurs fiscaux + export CSV (RG-8, RG-11)."""

from datetime import date, datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.tax_tracking.repository import TaxTrackingRepository
from app.modules.trading_config.repository import TradingConfigRepository


class TaxTrackingService:
    def __init__(self, db: Session):
        self.tax_repo = TaxTrackingRepository(db)
        self.config_repo = TradingConfigRepository(db)

    def get_counters(self, user_id: int) -> dict:
        """Retourne les compteurs fiscaux actuels."""
        config = self.config_repo.get_or_create(user_id)
        monthly_count = self.tax_repo.get_monthly_trade_count(user_id)
        yearly_volume = self.tax_repo.get_yearly_fiat_volume(user_id)

        return {
            "monthly_trade_count": monthly_count,
            "monthly_trade_limit": config.max_trades_per_month,
            "yearly_fiat_volume": yearly_volume,
            "alert_threshold": config.tax_alert_threshold,
            "alert_reached": yearly_volume >= config.tax_alert_threshold,
        }

    def export_csv(
        self,
        user_id: int,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> dict:
        """Génère les données d'export CSV (RG-11)."""
        dt_from = datetime.combine(date_from, datetime.min.time()) if date_from else None
        dt_to = datetime.combine(date_to, datetime.max.time()) if date_to else None

        trades = self.tax_repo.get_export_data(user_id, dt_from, dt_to)

        rows = []
        total = 0.0
        for t in trades:
            rows.append({
                "trade_id": t.id,
                "symbol": t.symbol,
                "trade_type": t.trade_type.value,
                "amount_fiat": t.amount_fiat,
                "quantity": t.quantity,
                "price": t.price,
                "executed_at": t.executed_at.isoformat(),
                "is_simulated": t.is_simulated,
            })
            total += t.amount_fiat

        return {
            "filename": f"tax_export_{date.today().isoformat()}.csv",
            "headers": [
                "trade_id", "symbol", "trade_type", "amount_fiat",
                "quantity", "price", "executed_at", "is_simulated",
            ],
            "rows": rows,
            "total_amount_fiat": round(total, 2),
            "period_from": date_from,
            "period_to": date_to,
        }
