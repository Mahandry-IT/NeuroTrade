"""DTOs tax_tracking — compteurs fiscaux + export (RG-8, RG-11)."""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel


class TaxCounterResponse(BaseModel):
    """Compteurs fiscaux actuels."""
    monthly_trade_count: int  # RG-8 : nombre de trades ce mois
    monthly_trade_limit: int
    yearly_fiat_volume: float  # RG-11 : volume fiat converti cette année
    alert_threshold: float
    alert_reached: bool  # yearly_fiat_volume >= alert_threshold


class TaxExportRow(BaseModel):
    """Ligne d'export CSV (RG-11)."""
    trade_id: int
    symbol: str
    trade_type: str
    amount_fiat: float
    quantity: float
    price: float
    executed_at: str  # ISO format
    is_simulated: bool


class TaxExportResponse(BaseModel):
    """Réponse d'export — liste de lignes CSV."""
    filename: str
    headers: List[str]
    rows: List[TaxExportRow]
    total_amount_fiat: float
    period_from: Optional[date] = None
    period_to: Optional[date] = None
