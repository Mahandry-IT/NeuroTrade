"""DTOs market_scanner — paires candidat scored par potentiel de profit."""

from pydantic import BaseModel, Field


class MarketCandidate(BaseModel):
    """Paire d'actifs classée par score de profitabilité."""

    pair: str = Field(description="Symbole Kraken (ex: XXBTZUSD)")
    altname: str = Field(description="Nom alternatif (ex: XBTUSD)")
    last_price: float = Field(description="Prix actuel (last trade)")
    bid: float = Field(description="Best bid")
    ask: float = Field(description="Best ask")
    volume_24h: float = Field(description="Volume de trading 24h (en base)")
    volume_24h_quote: float = Field(default=0.0, description="Volume 24h en quote (fiat)")
    spread_pct: float = Field(description="Spread bid/ask en %")
    volatility_pct: float = Field(description="Volatilité proxy (range high/low) en %")
    score: float = Field(ge=0, le=100, description="Score composite de profitabilité (0-100)")
    score_volume: float = Field(default=0.0, description="Score composant volume (0-100)")
    score_spread: float = Field(default=0.0, description="Score composant spread (0-100)")
    score_volatility: float = Field(default=0.0, description="Score composant volatilité (0-100)")
