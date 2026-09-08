"""Router market_scanner — endpoint preview pour le scan de marchés."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user_id
from app.modules.kraken.client import KrakenSpotClient
from app.modules.market_scanner.service import MarketScannerService

router = APIRouter(prefix="/markets", tags=["market_scanner"])


@router.get("/scan")
def scan_markets(
    quote_currency: str = Query(default="USD", min_length=2, max_length=10),
    top_n: int = Query(default=10, ge=1, le=50),
    min_volume: float = Query(default=10_000.0, ge=0),
    user_id: int = Depends(get_current_user_id),
):
    """Preview des marchés les plus bénéfiques — read-only, pas de trading.

    Retourne les paires Kraken classées par score de profitabilité.
    Utile pour debugger le scanner avant d'activer l'auto-discover.
    """
    client = KrakenSpotClient()
    scanner = MarketScannerService(client)
    candidates = scanner.scan(
        quote_currency=quote_currency,
        top_n=top_n,
        min_volume_24h=min_volume,
        cache_ttl=0,  # pas de cache pour le preview
    )
    return {
        "quote_currency": quote_currency,
        "total_candidates": len(candidates),
        "candidates": [c.model_dump() for c in candidates],
    }
