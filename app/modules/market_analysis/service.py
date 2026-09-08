"""Service market_analysis — indicateurs techniques + interprétation Gemini (RG-4).

Architecture :
1. Calcul indicateurs techniques en Python pur (RSI, MACD, SMA/EMA) — pas d'appel LLM
2. Interprétation Gemini 1 appel par cycle et par actif candidat (throttlé)
3. Fallback rule-based si quota Gemini atteint — ne bloque jamais la boucle RG-4/RG-6
"""

import logging
import time
from collections import deque
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.market_analysis.repository import MarketAnalysisRepository

logger = logging.getLogger(__name__)

# ── Gemini rate-limit tracking (free tier) ──
_gemini_call_timestamps: deque = deque()
_gemini_daily_count: int = 0
_gemini_daily_reset_date: Optional[str] = None


def _gemini_throttle() -> bool:
    """Vérifie si un appel Gemini est possible (respect RPM + RPD)."""
    global _gemini_daily_count, _gemini_daily_reset_date

    now = time.time()
    today = time.strftime("%Y-%m-%d")

    # Reset compteur journalier
    if _gemini_daily_reset_date != today:
        _gemini_daily_count = 0
        _gemini_daily_reset_date = today

    # Vérifier RPD
    if _gemini_daily_count >= settings.gemini_rpd_limit:
        return False

    # Nettoyer les timestamps > 60s
    while _gemini_call_timestamps and _gemini_call_timestamps[0] < now - 60:
        _gemini_call_timestamps.popleft()

    # Vérifier RPM
    if len(_gemini_call_timestamps) >= settings.gemini_rpm_limit:
        return False

    return True


def _record_gemini_call() -> None:
    global _gemini_daily_count
    _gemini_call_timestamps.append(time.time())
    _gemini_daily_count += 1


# ── Technical indicators (Python pur) ──

def compute_rsi(prices: list[float], period: int = 14) -> Optional[float]:
    """RSI — Relative Strength Index."""
    if len(prices) < period + 1:
        return None
    deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
    gains = [d if d > 0 else 0 for d in deltas[-period:]]
    losses = [-d if d < 0 else 0 for d in deltas[-period:]]
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def compute_ema(prices: list[float], period: int) -> Optional[float]:
    """EMA — Exponential Moving Average."""
    if len(prices) < period:
        return None
    multiplier = 2 / (period + 1)
    ema = sum(prices[:period]) / period
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return round(ema, 6)


def compute_sma(prices: list[float], period: int) -> Optional[float]:
    """SMA — Simple Moving Average."""
    if len(prices) < period:
        return None
    return round(sum(prices[-period:]) / period, 6)


def compute_macd(
    prices: list[float], fast: int = 12, slow: int = 26, signal: int = 9
) -> Optional[dict]:
    """MACD — Moving Average Convergence Divergence."""
    if len(prices) < slow + signal:
        return None
    ema_fast = compute_ema(prices, fast)
    ema_slow = compute_ema(prices, slow)
    if ema_fast is None or ema_slow is None:
        return None
    macd_line = round(ema_fast - ema_slow, 6)

    # Simplified signal line (for full impl, need historical MACD values)
    return {
        "macd": macd_line,
        "macd_signal": None,  # needs historical data
        "macd_histogram": None,
    }


class MarketAnalysisService:
    def __init__(self, db: Session, kraken_client=None):
        self.repo = MarketAnalysisRepository(db)
        self._kraken_client = kraken_client

    def compute_indicators(self, symbol: str, prices: list[float]) -> dict:
        """Calcule tous les indicateurs techniques en Python pur (pas d'appel LLM)."""
        indicators = {
            "rsi": compute_rsi(prices),
            "sma_short": compute_sma(prices, 10),
            "sma_long": compute_sma(prices, 30),
            "ema_short": compute_ema(prices, 10),
            "ema_long": compute_ema(prices, 30),
            "macd": None,
        }
        macd = compute_macd(prices)
        if macd:
            indicators["macd"] = macd["macd"]
            indicators["macd_signal"] = macd.get("macd_signal")
            indicators["macd_histogram"] = macd.get("macd_histogram")

        return indicators

    def get_real_prices(self, pair: str, count: int = 100) -> list[float]:
        """Récupère les prix réels via KrakenSpotClient (public).

        Utilise les données OHLC pour calculer les indicateurs.
        Fallback sur une liste vide si l'appel échoue.
        """
        if not self._kraken_client:
            return []
        try:
            candles = self._kraken_client.get_ohlc(pair, interval=60)
            return [c.close for c in candles[-count:]]
        except Exception as e:
            logger.error("kraken_ohlc_error pair=%s error=%s", pair, str(e))
            return []

    def get_current_price(self, pair: str) -> Optional[float]:
        """Récupère le prix actuel via KrakenSpotClient (public)."""
        if not self._kraken_client:
            return None
        try:
            ticker = self._kraken_client.get_ticker_price(pair)
            return ticker.last_price if ticker else None
        except Exception as e:
            logger.error("kraken_ticker_error pair=%s error=%s", pair, str(e))
            return None

    def analyze(
        self, symbol: str, prices: list[float]
    ) -> dict:
        """Cycle complet : indicateurs → Gemini interprétation ou fallback rule-based."""
        # Si pas de prix fournis, tenter de récupérer via Kraken
        if not prices and self._kraken_client:
            prices = self.get_real_prices(symbol)

        indicators = self.compute_indicators(symbol, prices)

        # Sauvegarder le signal en base
        self.repo.save_signal(
            symbol=symbol,
            rsi=indicators.get("rsi"),
            macd=indicators.get("macd"),
            macd_signal=indicators.get("macd_signal"),
            macd_histogram=indicators.get("macd_histogram"),
            sma_short=indicators.get("sma_short"),
            sma_long=indicators.get("sma_long"),
            ema_short=indicators.get("ema_short"),
            ema_long=indicators.get("ema_long"),
        )

        # Tenter Gemini pour l'interprétation
        gemini_result = self._try_gemini_interpretation(symbol, indicators)

        if gemini_result:
            return {
                "symbol": symbol,
                "indicators": indicators,
                "source": "gemini",
                "signal": gemini_result,
            }

        # Fallback rule-based — ne bloque jamais la boucle
        return {
            "symbol": symbol,
            "indicators": indicators,
            "source": "rule_based",
            "signal": self._rule_based_signal(indicators),
        }

    def _try_gemini_interpretation(self, symbol: str, indicators: dict) -> Optional[str]:
        """Appel Gemini throttlé pour interpréter les signaux (1 appel par cycle/actif)."""
        if not _gemini_throttle():
            logger.warning("gemini_quota_reached symbol=%s — using fallback", symbol)
            return None

        try:
            from google import genai
            client = genai.Client(api_key=settings.gemini_api_key)
            prompt = (
                f"Analyse technique pour {symbol}:\n"
                f"RSI: {indicators.get('rsi')}, "
                f"SMA10: {indicators.get('sma_short')}, SMA30: {indicators.get('sma_long')}, "
                f"EMA10: {indicators.get('ema_short')}, EMA30: {indicators.get('ema_long')}, "
                f"MACD: {indicators.get('macd')}\n"
                "Réponds UNIQUEMENT par: BUY, SELL, ou HOLD avec une raison courte."
            )

            response = client.models.generate_content(model="gemini-3.6-flash", contents=prompt)
            _record_gemini_call()
            return response.text.strip()

        except Exception as e:
            logger.error("gemini_error symbol=%s error=%s", symbol, str(e))
            return None

    def _rule_based_signal(self, indicators: dict) -> str:
        """Fallback rule-based : décision uniquement sur indicateurs (sans LLM)."""
        rsi = indicators.get("rsi")
        sma_short = indicators.get("sma_short")
        sma_long = indicators.get("sma_long")
        ema_short = indicators.get("ema_short")
        ema_long = indicators.get("ema_long")

        buy_signals = 0
        sell_signals = 0

        # RSI
        if rsi is not None:
            if rsi < 30:
                buy_signals += 1
            elif rsi > 70:
                sell_signals += 1

        # SMA crossover
        if sma_short and sma_long:
            if sma_short > sma_long:
                buy_signals += 1
            else:
                sell_signals += 1

        # EMA crossover
        if ema_short and ema_long:
            if ema_short > ema_long:
                buy_signals += 1
            else:
                sell_signals += 1

        if buy_signals >= 2 and buy_signals > sell_signals:
            return "BUY"
        elif sell_signals >= 2 and sell_signals > buy_signals:
            return "SELL"
        return "HOLD"
