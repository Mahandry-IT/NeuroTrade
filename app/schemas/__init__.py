"""DTOs Pydantic transverses — point d'entrée unique."""

from app.schemas.auth import (
    UserCreate, UserLogin, UserResponse, TokenResponse,
    PlatformConnectRequest, PlatformStatusResponse,
)
from app.schemas.trading_config import (
    TradingConfigUpdate, TradingConfigResponse,
    BotStatusResponse, BotControlResponse, SimulationModeUpdate,
)
from app.schemas.trading_engine import PositionResponse, TradeResponse
from app.schemas.history import (
    PaginatedResponse, PaginationMeta, HistoryExportQuery, HistoryStatsResponse,
)
from app.schemas.tax_tracking import (
    TaxCounterResponse, TaxExportRow, TaxExportResponse,
)

__all__ = [
    "UserCreate", "UserLogin", "UserResponse", "TokenResponse",
    "PlatformConnectRequest", "PlatformStatusResponse",
    "TradingConfigUpdate", "TradingConfigResponse",
    "BotStatusResponse", "BotControlResponse", "SimulationModeUpdate",
    "PositionResponse", "TradeResponse",
    "PaginatedResponse", "PaginationMeta", "HistoryExportQuery", "HistoryStatsResponse",
    "TaxCounterResponse", "TaxExportRow", "TaxExportResponse",
]
