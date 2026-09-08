"""Tests unitaires market_analysis — indicateurs techniques + fallback rule-based."""

from app.modules.market_analysis.service import (
    compute_rsi, compute_sma, compute_ema, compute_macd,
    MarketAnalysisService,
)


class TestTechnicalIndicators:
    """Tests des calculateurs d'indicateurs (Python pur, pas de LLM)."""

    def test_rsi_overbought(self):
        prices = list(range(1, 30))  # tendance haussière → RSI élevé
        rsi = compute_rsi(prices)
        assert rsi is not None
        assert rsi > 70  # overbought

    def test_rsi_oversold(self):
        prices = list(range(30, 1, -1))  # tendance baissière → RSI bas
        rsi = compute_rsi(prices)
        assert rsi is not None
        assert rsi < 30  # oversold

    def test_rsi_insufficient_data(self):
        prices = [100, 101, 102]  # pas assez de données
        rsi = compute_rsi(prices)
        assert rsi is None

    def test_sma_basic(self):
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        sma = compute_sma(prices, 3)
        assert sma == 40.0  # (30+40+50)/3

    def test_sma_insufficient_data(self):
        prices = [10.0, 20.0]
        sma = compute_sma(prices, 5)
        assert sma is None

    def test_ema_basic(self):
        prices = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]
        ema = compute_ema(prices, 3)
        assert ema is not None
        assert isinstance(ema, float)

    def test_macd_insufficient_data(self):
        prices = list(range(10))
        macd = compute_macd(prices)
        assert macd is None


class TestRuleBasedSignal:
    """Tests du fallback rule-based (sans Gemini)."""

    def test_buy_signal_strong_uptrend(self):
        """RSI bas + SMA/EMA croisés haussiers → BUY."""
        service = MarketAnalysisService.__new__(MarketAnalysisService)
        indicators = {
            "rsi": 25.0,  # oversold
            "sma_short": 105.0,
            "sma_long": 100.0,  # SMA short > long
            "ema_short": 106.0,
            "ema_long": 101.0,  # EMA short > long
            "macd": 2.0,
        }
        signal = service._rule_based_signal(indicators)
        assert signal == "BUY"

    def test_sell_signal_strong_downtrend(self):
        """RSI haut + SMA/EMA croisés baissiers → SELL."""
        service = MarketAnalysisService.__new__(MarketAnalysisService)
        indicators = {
            "rsi": 75.0,  # overbought
            "sma_short": 95.0,
            "sma_long": 100.0,  # SMA short < long
            "ema_short": 94.0,
            "ema_long": 99.0,  # EMA short < long
            "macd": -2.0,
        }
        signal = service._rule_based_signal(indicators)
        assert signal == "SELL"

    def test_hold_signal_mixed(self):
        """Signaux mixtes → HOLD."""
        service = MarketAnalysisService.__new__(MarketAnalysisService)
        indicators = {
            "rsi": 50.0,  # neutre
            "sma_short": 105.0,
            "sma_long": 100.0,  # buy
            "ema_short": 94.0,
            "ema_long": 99.0,  # sell
            "macd": 0.0,
        }
        signal = service._rule_based_signal(indicators)
        assert signal == "HOLD"

    def test_hold_signal_no_data(self):
        """Aucun indicateur disponible → HOLD."""
        service = MarketAnalysisService.__new__(MarketAnalysisService)
        indicators = {
            "rsi": None,
            "sma_short": None,
            "sma_long": None,
            "ema_short": None,
            "ema_long": None,
            "macd": None,
        }
        signal = service._rule_based_signal(indicators)
        assert signal == "HOLD"
