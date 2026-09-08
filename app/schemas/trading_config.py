"""DTOs trading_config — validation des paramètres de trading."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class TradingConfigUpdate(BaseModel):
    """Mise à jour partielle de la configuration de trading."""
    gain_limit_pct: Optional[float] = Field(None, gt=0, le=100)
    loss_limit_pct: Optional[float] = Field(None, lt=0, ge=-100)
    capital_pct_per_trade: Optional[float] = Field(None, gt=0, le=100)
    max_trades_per_month: Optional[int] = Field(None, gt=0, le=500)
    min_holding_duration: Optional[int] = Field(None, ge=0)  # en minutes
    tax_alert_threshold: Optional[float] = Field(None, ge=0)
    kraken_pair: Optional[str] = Field(None, min_length=3, max_length=20)
    # Market Scanner
    auto_discover_markets: Optional[bool] = None
    max_concurrent_positions: Optional[int] = Field(None, ge=1, le=20)
    quote_currency: Optional[str] = Field(None, min_length=2, max_length=10)

    @field_validator("quote_currency")
    @classmethod
    def normalize_quote_currency(cls, v: str | None) -> str | None:
        """Normalize and validate quote_currency against supported list."""
        if v is None:
            return v
        upper = v.upper().strip()
        # Legacy code normalization (ZUSD -> USD)
        _legacy = {"ZUSD": "USD", "ZEUR": "EUR", "ZGBP": "GBP",
                    "ZCAD": "CAD", "ZAUD": "AUD", "ZJPY": "JPY", "ZCHF": "CHF"}
        upper = _legacy.get(upper, upper)
        _supported = {"USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF",
                       "USDT", "USDC", "DAI"}
        if upper not in _supported:
            raise ValueError(
                f"Unsupported quote_currency '{v}'. Supported: {sorted(_supported)}"
            )
        return upper
    min_volume_24h: Optional[float] = Field(None, ge=0)
    scanner_cache_ttl: Optional[int] = Field(None, ge=60, le=3600)


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
    kraken_pair: str
    # Market Scanner
    auto_discover_markets: bool
    max_concurrent_positions: int
    quote_currency: str
    min_volume_24h: float
    scanner_cache_ttl: int
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
