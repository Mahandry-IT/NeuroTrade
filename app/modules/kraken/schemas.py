"""DTOs Kraken — schémas de réponse de l'API Kraken Spot."""

from typing import Optional

from pydantic import BaseModel, Field


# ── Public endpoints ──


class KrakenTickerPrice(BaseModel):
    """Prix actuel d'un actif (endpoint Ticker)."""
    symbol: str
    bid: float = Field(description="Best bid price")
    ask: float = Field(description="Best ask price")
    last_price: float = Field(description="Last trade price")
    volume_24h: float = Field(description="24h trading volume")


class KrakenAssetPair(BaseModel):
    """Informations sur une paire d'actifs."""
    altname: str  # ex: XBTUSD
    wsname: str   # ex: XBT/USD
    base: str     # ex: XXBT
    quote: str    # ex: ZUSD
    lot: str
    pair_decimals: int
    lot_decimals: int
    leverage_min: Optional[int] = None
    leverage_max: Optional[int] = None
    fees: list = []
    fees_maker: list = []


class KrakenOHLC(BaseModel):
    """Bougie OHLC (Open, High, Low, Close)."""
    time: float
    open: float
    high: float
    low: float
    close: float
    vwap: float
    volume: float
    count: int


# ── Private endpoints ──


class KrakenBalance(BaseModel):
    """Solde d'un actif (endpoint Balance, privé)."""
    asset: str
    balance: float
    hold: float = Field(default=0.0, description="Montant en ordres ouverts")


class KrakenAddOrderResult(BaseModel):
    """Résultat d'un ordre ajouté (endpoint AddOrder, privé)."""
    order_id: str
    descr: dict = {}


class KrakenOrderInfo(BaseModel):
    """Info détaillée d'un ordre (endpoint QueryOrders, privé)."""
    order_id: str
    status: str  # open, closed, canceled, expired
    descr: dict = {}
    price: Optional[float] = None
    vol: Optional[float] = None
    vol_exec: Optional[float] = None
    cost: Optional[float] = None
    fee: Optional[float] = None
    close_time: Optional[float] = None


# ── Common ──


class KrakenError(BaseModel):
    """Erreur retournée par l'API Kraken."""
    error: list[str] = []


class ExecutionResult(BaseModel):
    """Résultat unifié d'exécution d'ordre (simulation ou réel)."""
    success: bool
    order_id: Optional[str] = None
    fill_price: float = 0.0
    quantity: float = 0.0
    fee: float = 0.0
    is_simulated: bool = True
    error_message: Optional[str] = None
