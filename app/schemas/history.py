"""DTOs history — historique trades + stats performance."""

from datetime import date, datetime
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """Réponse paginée standardisée."""
    data: List[T]
    meta: "PaginationMeta"


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total: int
    total_pages: int


class HistoryExportQuery(BaseModel):
    """Filtres pour l'export historique."""
    page: int = Field(default=1, ge=1)
    limit: int = Field(default=20, ge=1, le=100)
    is_simulated: Optional[bool] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    symbol: Optional[str] = None


class HistoryStatsResponse(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    total_gain_fiat: float
    total_loss_fiat: float
    net_pnl_fiat: float
    period_from: Optional[datetime] = None
    period_to: Optional[datetime] = None
