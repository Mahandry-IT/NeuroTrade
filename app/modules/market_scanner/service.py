"""Service market_scanner — découverte et scoring des marchés les plus bénéfiques.

Architecture :
1. Récupère toutes les paires Kraken via get_asset_pairs() (1 appel)
2. Filtre par devise de cotation (USD, EUR, etc.)
3. Récupère les données ticker pour chaque paire (N appels, throttlés)
4. Calcule un score composite (volume + spread + volatilité)
5. Cache les résultats en mémoire avec TTL configurable
6. Retourne le top N trié par score décroissant
"""

import logging
import time
from typing import Optional

from app.modules.kraken.client import KrakenSpotClient
from app.modules.market_scanner.schemas import MarketCandidate

logger = logging.getLogger(__name__)

# ── Supported quote currencies (display names) ──
SUPPORTED_QUOTES = frozenset({
    "USD", "EUR", "GBP", "CAD", "AUD", "JPY", "CHF",
    "USDT", "USDC", "DAI",
})

# ── Legacy-to-display mapping (fallback if assetVersion=1 fails) ──
_LEGACY_QUOTE_MAP: dict[str, str] = {
    "ZUSD": "USD", "ZEUR": "EUR", "ZGBP": "GBP",
    "ZCAD": "CAD", "ZAUD": "AUD", "ZJPY": "JPY",
    "ZCHF": "CHF",
}

def normalize_kraken_asset(code: str) -> str:
    """Strip Kraken legacy prefixes (Z/X) and return the display name.

    Examples: ZUSD -> USD, XXBT -> BTC, XETH -> ETH, ADA -> ADA
    """
    upper = code.upper()
    # Check quote-specific legacy mapping first
    if upper in _LEGACY_QUOTE_MAP:
        return _LEGACY_QUOTE_MAP[upper]
    # Strip Z prefix for fiat (ZUSD -> USD, ZEUR -> EUR)
    if upper.startswith("Z") and len(upper) > 1:
        stripped = upper[1:]
        if stripped in SUPPORTED_QUOTES:
            return stripped
    # Strip X prefix for crypto (XXBT -> BTC, XETH -> ETH)
    if upper.startswith("X") and len(upper) > 1:
        stripped = upper[1:]
        # Common Kraken legacy crypto codes
        _crypto_map = {"XBT": "BTC", "XETH": "ETH"}
        return _crypto_map.get(upper, stripped)
    return upper

# ── Poids du scoring composite ──
WEIGHT_VOLUME = 0.40
WEIGHT_SPREAD = 0.30
WEIGHT_VOLATILITY = 0.30

# ── Seuils de normalisation (plancher/plafond) ──
MIN_VOLUME_FOR_SCORE = 100.0       # volume 24h minimum pour scoring
MAX_VOLUME_FOR_SCORE = 1_000_000.0  # volume plafond (score max au-delà)
MIN_SPREAD_PCT = 0.01              # spread minimum réaliste
MAX_SPREAD_PCT = 5.0               # spread max (score 0 au-delà)
MIN_VOLATILITY_PCT = 0.1           # volatilité minimum
MAX_VOLATILITY_PCT = 30.0          # volatilité max (score 100 au-delà)


class MarketScannerService:
    """Scanne les paires Kraken, calcule un score de profitabilité, retourne le top N.

    Args:
        kraken_client: client HTTP Kraken (public endpoints uniquement).
    """

    def __init__(self, kraken_client: KrakenSpotClient):
        self._client = kraken_client
        self._cache: dict[str, tuple[float, list[MarketCandidate]]] = {}
        self._consecutive_no_pairs = 0  # tracks repeated scanner_no_pairs across cycles

    def scan(
        self,
        quote_currency: str = "USD",
        top_n: int = 5,
        min_volume_24h: float = 10_000.0,
        cache_ttl: int = 300,
    ) -> list[MarketCandidate]:
        """Scanne et classe les paires par potentiel de profit.

        Args:
            quote_currency: devise de cotation (ex: "USD", "EUR").
            top_n: nombre de candidats à retourner.
            min_volume_24h: volume minimum 24h (en base) pour être candidat.
            cache_ttl: durée du cache en secondes (0 = pas de cache).

        Returns:
            Liste des top_n MarketCandidate triés par score décroissant.
        """
        cache_key = f"{quote_currency}:{top_n}:{min_volume_24h}"

        # Vérifier le cache
        if cache_ttl > 0 and cache_key in self._cache:
            cached_at, cached_data = self._cache[cache_key]
            if time.time() - cached_at < cache_ttl:
                logger.info(
                    "scanner_cache_hit key=%s candidates=%d",
                    cache_key, len(cached_data),
                )
                return cached_data

        # Étape 1 : récupérer toutes les paires
        try:
            raw_pairs = self._client.get_asset_pairs()
        except Exception as e:
            logger.error("scanner_asset_pairs_error error=%s", str(e))
            return []

        # Étape 2 : filtrer par devise de cotation
        quote_upper = quote_currency.upper()
        raw_count = len(raw_pairs)
        filtered_pairs = {}
        for pair_name, pair_data in raw_pairs.items():
            quote = pair_data.get("quote", "")
            # Normalize legacy Kraken codes (ZUSD -> USD) if needed
            normalized_quote = normalize_kraken_asset(quote)
            # Filtrer : paires avec la bonne devise, pas de leverage, pas de staking
            if normalized_quote != quote_upper:
                continue
            pair_type = pair_data.get("pair_type", "")
            if pair_type in ("margin", "futures", "staking"):
                continue
            # Ignorer les paires inverses (ex: USDZEUR)
            base = pair_data.get("base", "")
            if normalize_kraken_asset(base) == quote_upper:
                continue
            filtered_pairs[pair_name] = pair_data

        if not filtered_pairs:
            self._consecutive_no_pairs += 1
            level = logging.ERROR if self._consecutive_no_pairs >= 3 else logging.WARNING
            logger.log(level,
                "scanner_no_pairs quote=%s raw_pairs_count=%d consecutive=%d",
                quote_upper, raw_count, self._consecutive_no_pairs,
            )
            return []

        # Reset counter on success
        if self._consecutive_no_pairs > 0:
            logger.info("scanner_pairs_found quote=%s after %d empty cycles",
                quote_upper, self._consecutive_no_pairs)
        self._consecutive_no_pairs = 0

        logger.info(
            "scanner_pairs_filtered quote=%s count=%d",
            quote_currency, len(filtered_pairs),
        )

        # Étape 3 : récupérer les tickers (batch limité à éviter rate limit)
        candidates: list[MarketCandidate] = []
        batch_size = 20
        pair_names = list(filtered_pairs.keys())

        for i in range(0, len(pair_names), batch_size):
            batch = pair_names[i : i + batch_size]
            for pair_name in batch:
                candidate = self._score_pair(pair_name, filtered_pairs[pair_name])
                if candidate and candidate.volume_24h >= min_volume_24h:
                    candidates.append(candidate)
                # Petit délai entre batches pour respecter les rate limits
            if i + batch_size < len(pair_names):
                time.sleep(0.1)

        # Étape 4 : trier par score décroissant
        candidates.sort(key=lambda c: c.score, reverse=True)
        result = candidates[:top_n]

        # Mettre en cache
        if cache_ttl > 0:
            self._cache[cache_key] = (time.time(), result)

        logger.info(
            "scanner_complete quote=%s scanned=%d qualified=%d returned=%d",
            quote_currency, len(filtered_pairs), len(candidates), len(result),
        )

        return result

    def _score_pair(
        self,
        pair_name: str,
        pair_data: dict,
    ) -> Optional[MarketCandidate]:
        """Récupère le ticker d'une paire et calcule son score."""
        try:
            ticker = self._client.get_ticker(pair_name)
        except Exception as e:
            logger.debug("scanner_ticker_error pair=%s error=%s", pair_name, str(e))
            return None

        if not ticker:
            return None

        # Extraire les données du ticker Kraken
        # Format Kraken : "b" = [bid, whole_lot_volume, lot_volume]
        #                 "a" = [ask, whole_lot_volume, lot_volume]
        #                 "c" = [last_trade_price, lot_volume]
        #                 "v" = [today, last_24h] — volume
        #                 "h" = [today, last_24h] — high
        #                 "l" = [today, last_24h] — low
        try:
            bid = float(ticker.get("b", [0])[0])
            ask = float(ticker.get("a", [0])[0])
            last_price = float(ticker.get("c", [0])[0])
            volume_24h = float(ticker.get("v", [0, 0])[1])
            high_24h = float(ticker.get("h", [0, 0])[1])
            low_24h = float(ticker.get("l", [0, 0])[1])
        except (IndexError, ValueError, TypeError):
            logger.debug("scanner_ticker_parse_error pair=%s", pair_name)
            return None

        if last_price <= 0 or bid <= 0 or ask <= 0:
            return None

        # Calculer le spread
        mid_price = (bid + ask) / 2
        spread_pct = ((ask - bid) / mid_price) * 100 if mid_price > 0 else 999.0

        # Calculer la volatilité proxy (range high/low)
        volatility_pct = ((high_24h - low_24h) / low_24h) * 100 if low_24h > 0 else 0.0

        # Volume en quote (estimation)
        volume_24h_quote = volume_24h * last_price

        # Scoring composite
        score_volume = self._normalize_score(
            volume_24h, MIN_VOLUME_FOR_SCORE, MAX_VOLUME_FOR_SCORE
        )
        # Spread : inverse (spread faible = bon score)
        score_spread = self._invert_and_normalize(
            spread_pct, MIN_SPREAD_PCT, MAX_SPREAD_PCT
        )
        score_volatility = self._normalize_score(
            volatility_pct, MIN_VOLATILITY_PCT, MAX_VOLATILITY_PCT
        )

        score = (
            score_volume * WEIGHT_VOLUME
            + score_spread * WEIGHT_SPREAD
            + score_volatility * WEIGHT_VOLATILITY
        )

        altname = pair_data.get("altname", pair_name)

        return MarketCandidate(
            pair=pair_name,
            altname=altname,
            last_price=last_price,
            bid=bid,
            ask=ask,
            volume_24h=volume_24h,
            volume_24h_quote=volume_24h_quote,
            spread_pct=round(spread_pct, 4),
            volatility_pct=round(volatility_pct, 2),
            score=round(score, 2),
            score_volume=round(score_volume, 2),
            score_spread=round(score_spread, 2),
            score_volatility=round(score_volatility, 2),
        )

    @staticmethod
    def _normalize_score(value: float, min_val: float, max_val: float) -> float:
        """Normalise une valeur entre 0 et 100 (clamped)."""
        if max_val <= min_val:
            return 0.0
        normalized = (value - min_val) / (max_val - min_val) * 100
        return max(0.0, min(100.0, normalized))

    @staticmethod
    def _invert_and_normalize(value: float, min_val: float, max_val: float) -> float:
        """Normalise inversée : plus la valeur est basse, meilleur est le score."""
        if max_val <= min_val:
            return 0.0
        normalized = (1 - (value - min_val) / (max_val - min_val)) * 100
        return max(0.0, min(100.0, normalized))

    def clear_cache(self) -> None:
        """Vide le cache — utile pour les tests."""
        self._cache.clear()
