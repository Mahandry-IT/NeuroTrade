"""DTOs trading_engine — positions et trades."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class PositionResponse(BaseModel):
    id: int
    symbol: str
    amount: float
    quantity: float
    entry_price: float
    opened_at: datetime
    closed_at: Optional[datetime] = None
    status: str
    is_simulated: bool

    model_config = {"from_attributes": True}


class TradeResponse(BaseModel):
    id: int
    position_id: int
    trade_type: str
    symbol: str
    amount_fiat: float
    quantity: float
    price: float
    executed_at: datetime
    result: str
    is_simulated: bool
    notes: Optional[str] = None

    model_config = {"from_attributes": True}
