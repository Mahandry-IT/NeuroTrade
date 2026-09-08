"""DTOs trading_config — validation des paramètres de trading."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TradingConfigUpdate(BaseModel):
    """Mise à jour partielle de la configuration de trading."""
    gain_limit_pct: Optional[float] = Field(None, gt=0, le=100)
    loss_limit_pct: Optional[float] = Field(None, lt=0, ge=-100)
    capital_pct_per_trade: Optional[float] = Field(None, gt=0, le=100)
    max_trades_per_month: Optional[int] = Field(None, gt=0, le=500)
    min_holding_duration: Optional[int] = Field(None, ge=0)  # en minutes
    tax_alert_threshold: Optional[float] = Field(None, ge=0)


class TradingConfigResponse(BaseModel):
    id: int
    user_id: int
    gain_limit_pct: float
    loss_limit_pct: float
    capital_pct_per_trade: float
    max_trades_per_month: int
    min_holding_duration: int
    tax_alert_threshold: float
    simulation_mode: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class BotStatusResponse(BaseModel):
    status: str  # running / stopped
    last_cycle_at: Optional[datetime] = None
    started_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BotControlResponse(BaseModel):
    status: str
    message: str


class SimulationModeUpdate(BaseModel):
    """Bascule simulation/réel — confirm obligatoire (RG-5)."""
    confirm: bool
    simulation_mode: bool
