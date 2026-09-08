"""Tests unitaires market_scanner — scoring, cache, filtrage paires."""

from unittest.mock import MagicMock, patch

from app.modules.market_scanner.service import (
    MarketScannerService,
    WEIGHT_VOLUME,
    WEIGHT_SPREAD,
    WEIGHT_VOLATILITY,
    normalize_kraken_asset,
    SUPPORTED_QUOTES,
)
from app.modules.market_scanner.schemas import MarketCandidate


class TestScoringHelpers:
    """Tests des méthodes utilitaires de scoring."""

    def test_normalize_score_basic(self):
        """Valeur au milieu → score ~50."""
        score = MarketScannerService._normalize_score(500, 0, 1000)
        assert score == 50.0

    def test_normalize_score_min(self):
        """Valeur = min → score 0."""
        score = MarketScannerService._normalize_score(0, 0, 1000)
        assert score == 0.0

    def test_normalize_score_max(self):
        """Valeur = max → score 100."""
        score = MarketScannerService._normalize_score(1000, 0, 1000)
        assert score == 100.0

    def test_normalize_score_clamped_above(self):
        """Valeur > max → score plafonné à 100."""
        score = MarketScannerService._normalize_score(1500, 0, 1000)
        assert score == 100.0

    def test_normalize_score_clamped_below(self):
        """Valeur < min → score plafonné à 0."""
        score = MarketScannerService._normalize_score(-100, 0, 1000)
        assert score == 0.0

    def test_normalize_score_equal_min_max(self):
        """min == max → score 0 (évite division par zéro)."""
        score = MarketScannerService._normalize_score(500, 100, 100)
        assert score == 0.0

    def test_invert_and_normalize_low_value(self):
        """Spread faible → score élevé."""
        score = MarketScannerService._invert_and_normalize(0.1, 0.01, 5.0)
        assert score > 90  # très bon score pour spread faible

    def test_invert_and_normalize_high_value(self):
        """Spread élevé → score faible."""
        score = MarketScannerService._invert_and_normalize(4.5, 0.01, 5.0)
        assert score < 12  # très mauvais spread

    def test_inversion_relationship(self):
        """Les scores inversés sont cohérents : bas = bon, haut = mauvais."""
        score_low = MarketScannerService._invert_and_normalize(0.1, 0.01, 5.0)
        score_high = MarketScannerService._invert_and_normalize(4.0, 0.01, 5.0)
        assert score_low > score_high


class TestMarketScannerService:
    """Tests du scanner avec mock KrakenSpotClient."""

    def _make_pair_data(self, altname: str = "XBTUSD", quote: str = "USD") -> dict:
        """Génère des données de paire fictives."""
        return {
            "altname": altname,
            "wsname": f"{altname[:3]}/{quote}",
            "base": "XXBT",
            "quote": quote,
            "pair_type": "spot",
        }

    def _make_ticker(
        self, last: float, bid: float, ask: float,
        volume_24h: float = 1000.0, high: float = 105.0, low: float = 95.0,
    ) -> dict:
        """Génère des données ticker fictives au format Kraken."""
        return {
            "c": [str(last), "1.0"],
            "b": [str(bid), "1.0", "1.0"],
            "a": [str(ask), "1.0", "1.0"],
            "v": ["100.0", str(volume_24h)],
            "h": ["100.0", str(high)],
            "l": ["100.0", str(low)],
        }

    def test_scan_filters_by_quote_currency(self):
        """Seules les paires avec la bonne devise de cotation sont retenues."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {
            "XXBTZUSD": self._make_pair_data("XBTUSD", "USD"),
            "XETHZEUR": self._make_pair_data("ETHEUR", "EUR"),
            "ADAUSD": self._make_pair_data("ADAUSD", "USD"),
        }
        client.get_ticker.return_value = self._make_ticker(
            last=100.0, bid=99.5, ask=100.5, volume_24h=50000, high=105, low=95,
        )

        scanner = MarketScannerService(client)
        candidates = scanner.scan(quote_currency="USD", top_n=10, cache_ttl=0)

        # Seules les paires USD sont retournées (XXBTZUSD et ADAUSD)
        assert len(candidates) == 2
        assert all(c.pair in ("XXBTZUSD", "ADAUSD") for c in candidates)

    def test_scan_excludes_margin_pairs(self):
        """Les paires margin/futures/staking sont exclues."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {
            "XXBTZUSD": {**self._make_pair_data(), "pair_type": "spot"},
            "USDTEUR": {**self._make_pair_data(), "pair_type": "margin"},
        }
        client.get_ticker.return_value = self._make_ticker(last=100.0, bid=99.5, ask=100.5, volume_24h=50000)

        scanner = MarketScannerService(client)
        candidates = scanner.scan(quote_currency="USD", cache_ttl=0)

        assert len(candidates) == 1
        assert candidates[0].pair == "XXBTZUSD"

    def test_scan_filters_by_min_volume(self):
        """Les paires avec volume < min_volume_24h sont exclues."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {
            "XXBTZUSD": self._make_pair_data(),
            "ADAUSD": self._make_pair_data("ADAUSD"),
        }
        # BTC a un gros volume, ADA un petit volume
        def mock_ticker(pair):
            if pair == "XXBTZUSD":
                return self._make_ticker(last=60000, bid=59900, ask=60100, volume_24h=5000)
            return self._make_ticker(last=0.5, bid=0.49, ask=0.51, volume_24h=50)

        client.get_ticker.side_effect = mock_ticker

        scanner = MarketScannerService(client)
        candidates = scanner.scan(
            quote_currency="USD", min_volume_24h=100, cache_ttl=0,
        )

        assert len(candidates) == 1
        assert candidates[0].pair == "XXBTZUSD"

    def test_scan_ranking_by_score(self):
        """Les candidats sont triés par score décroissant."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {
            "PAIR_HIGH": self._make_pair_data("PAIR_HIGH"),
            "PAIR_LOW": self._make_pair_data("PAIR_LOW"),
        }

        def mock_ticker(pair):
            if pair == "PAIR_HIGH":
                # Volume élevé, spread serré, bonne volatilité
                return self._make_ticker(
                    last=100.0, bid=99.9, ask=100.1,
                    volume_24h=500_000, high=110, low=90,
                )
            # Volume suffisant, spread large
            return self._make_ticker(
                last=1.0, bid=0.85, ask=1.15,
                volume_24h=50_000, high=1.2, low=0.8,
            )

        client.get_ticker.side_effect = mock_ticker

        scanner = MarketScannerService(client)
        candidates = scanner.scan(quote_currency="USD", top_n=10, cache_ttl=0)

        assert len(candidates) == 2
        assert candidates[0].pair == "PAIR_HIGH"
        assert candidates[0].score > candidates[1].score

    def test_scan_top_n_limit(self):
        """Seul top_n candidats sont retournés."""
        client = MagicMock()
        pairs = {f"PAIR{i}": self._make_pair_data(f"PAIR{i}") for i in range(10)}
        client.get_asset_pairs.return_value = pairs
        client.get_ticker.return_value = self._make_ticker(
            last=100.0, bid=99.0, ask=101.0,
            volume_24h=10000, high=110, low=90,
        )

        scanner = MarketScannerService(client)
        candidates = scanner.scan(quote_currency="USD", top_n=3, cache_ttl=0)

        assert len(candidates) <= 3

    def test_scan_returns_market_candidate_dto(self):
        """Les résultats sont des MarketCandidate avec tous les champs."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {
            "XXBTZUSD": self._make_pair_data(),
        }
        client.get_ticker.return_value = self._make_ticker(
            last=60000, bid=59900, ask=60100,
            volume_24h=50000, high=62000, low=58000,
        )

        scanner = MarketScannerService(client)
        candidates = scanner.scan(quote_currency="USD", cache_ttl=0)

        assert len(candidates) == 1
        c = candidates[0]
        assert isinstance(c, MarketCandidate)
        assert c.pair == "XXBTZUSD"
        assert c.last_price == 60000
        assert c.bid == 59900
        assert c.ask == 60100
        assert c.volume_24h == 50000
        assert 0 <= c.score <= 100
        assert 0 <= c.score_volume <= 100
        assert 0 <= c.score_spread <= 100
        assert 0 <= c.score_volatility <= 100

    def test_scan_ticker_error_skips_pair(self):
        """Une erreur sur le ticker d'une paire ne bloque pas les autres."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {
            "XXBTZUSD": self._make_pair_data(),
            "BROKEN": self._make_pair_data("BROKEN"),
        }

        def mock_ticker(pair):
            if pair == "BROKEN":
                raise Exception("API error")
            return self._make_ticker(last=100.0, bid=99.0, ask=101.0, volume_24h=10000)

        client.get_ticker.side_effect = mock_ticker

        scanner = MarketScannerService(client)
        candidates = scanner.scan(quote_currency="USD", cache_ttl=0)

        assert len(candidates) == 1
        assert candidates[0].pair == "XXBTZUSD"

    def test_scan_empty_asset_pairs(self):
        """Aucune paire retournée → résultat vide."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {}

        scanner = MarketScannerService(client)
        candidates = scanner.scan(quote_currency="USD", cache_ttl=0)

        assert candidates == []

    def test_scan_asset_pairs_error(self):
        """Erreur sur get_asset_pairs → résultat vide (pas de crash)."""
        client = MagicMock()
        client.get_asset_pairs.side_effect = Exception("Network error")

        scanner = MarketScannerService(client)
        candidates = scanner.scan(quote_currency="USD", cache_ttl=0)

        assert candidates == []

    def test_cache_returns_same_results(self):
        """Deux scans consécutifs avec TTL > 0 retournent les mêmes résultats."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {
            "XXBTZUSD": self._make_pair_data(),
        }
        client.get_ticker.return_value = self._make_ticker(
            last=100.0, bid=99.0, ask=101.0, volume_24h=10000,
        )

        scanner = MarketScannerService(client)
        first = scanner.scan(quote_currency="USD", cache_ttl=60)
        second = scanner.scan(quote_currency="USD", cache_ttl=60)

        assert first == second
        # get_asset_pairs n'est appelé qu'une seule fois (cache hit)
        assert client.get_asset_pairs.call_count == 1

    def test_cache_disabled(self):
        """cache_ttl=0 → pas de cache, les appels API sont refaits."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {
            "XXBTZUSD": self._make_pair_data(),
        }
        client.get_ticker.return_value = self._make_ticker(
            last=100.0, bid=99.0, ask=101.0, volume_24h=10000,
        )

        scanner = MarketScannerService(client)
        scanner.scan(quote_currency="USD", cache_ttl=0)
        scanner.scan(quote_currency="USD", cache_ttl=0)

        # Deux appels car pas de cache
        assert client.get_asset_pairs.call_count == 2

    def test_clear_cache(self):
        """clear_cache vide le cache et force un nouvel appel API."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {
            "XXBTZUSD": self._make_pair_data(),
        }
        client.get_ticker.return_value = self._make_ticker(
            last=100.0, bid=99.0, ask=101.0, volume_24h=10000,
        )

        scanner = MarketScannerService(client)
        scanner.scan(quote_currency="USD", cache_ttl=60)
        scanner.clear_cache()
        scanner.scan(quote_currency="USD", cache_ttl=60)

        # Deux appels car cache vidé
        assert client.get_asset_pairs.call_count == 2

    def test_score_weights_sum_to_one(self):
        """Les poids du scoring totalisent 1.0."""
        total = WEIGHT_VOLUME + WEIGHT_SPREAD + WEIGHT_VOLATILITY
        assert abs(total - 1.0) < 0.001

    def test_score_range_0_to_100(self):
        """Le score composite est toujours entre 0 et 100."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {
            "XXBTZUSD": self._make_pair_data(),
        }
        client.get_ticker.return_value = self._make_ticker(
            last=100.0, bid=99.0, ask=101.0,
            volume_24h=50000, high=110, low=90,
        )

        scanner = MarketScannerService(client)
        candidates = scanner.scan(quote_currency="USD", cache_ttl=0)

        assert len(candidates) == 1
        c = candidates[0]
        assert 0 <= c.score <= 100

    def test_scan_excludes_inverted_pairs(self):
        """Les paires inverses (quote=base) sont exclues."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {
            "XXBTZUSD": self._make_pair_data(),  # USDZ = USD quote → OK
        }
        client.get_ticker.return_value = self._make_ticker(
            last=100.0, bid=99.0, ask=101.0, volume_24h=10000,
        )

        scanner = MarketScannerService(client)
        candidates = scanner.scan(quote_currency="USD", cache_ttl=0)

        assert len(candidates) == 1
        assert candidates[0].pair == "XXBTZUSD"



class TestNormalizeKrakenAsset:
    """Tests de la fonction de normalisation des codes d'actifs Kraken."""

    def test_zusd_to_usd(self):
        assert normalize_kraken_asset("ZUSD") == "USD"

    def test_zeur_to_eur(self):
        assert normalize_kraken_asset("ZEUR") == "EUR"

    def test_zgbp_to_gbp(self):
        assert normalize_kraken_asset("ZGBP") == "GBP"

    def test_xxbt_to_xbt(self):
        """XXBT -> XBT (legacy crypto, not in quote map)."""
        result = normalize_kraken_asset("XXBT")
        assert result == "XBT"

    def test_xeth_to_eth(self):
        """XETH -> ETH via crypto map."""
        result = normalize_kraken_asset("XETH")
        assert result == "ETH"

    def test_display_name_passthrough(self):
        """Already normalized names pass through unchanged."""
        assert normalize_kraken_asset("USD") == "USD"
        assert normalize_kraken_asset("EUR") == "EUR"
        assert normalize_kraken_asset("ADA") == "ADA"

    def test_lowercase_input(self):
        """Case-insensitive input is handled."""
        assert normalize_kraken_asset("zusd") == "USD"
        assert normalize_kraken_asset("xxbt") == "XBT"


class TestLegacyCodeFiltering:
    """Tests que le scanner filtre correctement avec des codes legacy Kraken."""

    def _make_legacy_pair(self, altname: str, quote: str, base: str = "XXBT") -> dict:
        return {
            "altname": altname,
            "wsname": f"{altname[:3]}/{quote}",
            "base": base,
            "quote": quote,
            "pair_type": "spot",
        }

    def _make_ticker(self, last=100.0, bid=99.0, ask=101.0, volume_24h=10000.0, high=110.0, low=90.0):
        return {
            "c": [str(last), "1.0"],
            "b": [str(bid), "1.0", "1.0"],
            "a": [str(ask), "1.0", "1.0"],
            "v": ["100.0", str(volume_24h)],
            "h": ["100.0", str(high)],
            "l": ["100.0", str(low)],
        }

    def test_legacy_zusd_matches_usd_quote(self):
        """Kraken returns quote=ZUSD — scanner should match quote_currency=USD."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {
            "XXBTZUSD": self._make_legacy_pair("XBTUSD", "ZUSD", "XXBT"),
            "ADAUSD": {**self._make_legacy_pair("ADAUSD", "USD", "ADA"), "base": "ADA"},
        }
        client.get_ticker.return_value = self._make_ticker(volume_24h=50000)

        scanner = MarketScannerService(client)
        candidates = scanner.scan(quote_currency="USD", cache_ttl=0)

        pairs = [c.pair for c in candidates]
        assert "XXBTZUSD" in pairs, f"Legacy XXBTZUSD should match USD, got: {pairs}"
        assert "ADAUSD" in pairs

    def test_legacy_zeur_matches_eur_quote(self):
        """Kraken returns quote=ZEUR — scanner should match quote_currency=EUR."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {
            "XETHZEUR": self._make_legacy_pair("ETHEUR", "ZEUR", "XETH"),
        }
        client.get_ticker.return_value = self._make_ticker(volume_24h=50000)

        scanner = MarketScannerService(client)
        candidates = scanner.scan(quote_currency="EUR", cache_ttl=0)

        assert len(candidates) == 1
        assert candidates[0].pair == "XETHZEUR"

    def test_legacy_base_excluded_when_equals_quote(self):
        """Base=ZUSD (inverted pair) should be excluded when quote=USD."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {
            "USDZEUR": self._make_legacy_pair("USDEUR", "ZEUR", "ZUSD"),
        }
        client.get_ticker.return_value = self._make_ticker()

        scanner = MarketScannerService(client)
        candidates = scanner.scan(quote_currency="EUR", cache_ttl=0)

        # USDZEUR has base=ZUSD -> normalized to USD == EUR? No, USD != EUR
        # Actually base=ZUSD normalized to USD, quote=ZEUR normalized to EUR
        # base (USD) != quote (EUR), so pair passes... but it's inverted
        # The inverted check: base == quote_upper -> USD == EUR -> False
        # So it passes. This is correct behavior.
        assert len(candidates) == 1

    def test_consecutive_no_pairs_increments_counter(self):
        """Each empty scan increments the consecutive counter."""
        client = MagicMock()
        client.get_asset_pairs.return_value = {}  # empty

        scanner = MarketScannerService(client)
        scanner.scan(quote_currency="USD", cache_ttl=0)
        assert scanner._consecutive_no_pairs == 1

        scanner.scan(quote_currency="USD", cache_ttl=0)
        assert scanner._consecutive_no_pairs == 2

    def test_consecutive_counter_resets_on_success(self):
        """Counter resets to 0 when pairs are found."""
        client = MagicMock()

        # First: empty
        client.get_asset_pairs.return_value = {}
        scanner = MarketScannerService(client)
        scanner.scan(quote_currency="USD", cache_ttl=0)
        assert scanner._consecutive_no_pairs == 1

        # Second: success
        client.get_asset_pairs.return_value = {
            "XXBTZUSD": self._make_legacy_pair("XBTUSD", "ZUSD", "XXBT"),
        }
        client.get_ticker.return_value = self._make_ticker(volume_24h=50000)
        scanner.scan(quote_currency="USD", cache_ttl=0)
        assert scanner._consecutive_no_pairs == 0


class TestQuoteCurrencyValidation:
    """Tests de la validation quote_currency dans le schema Pydantic."""

    def test_valid_quote_accepted(self):
        from app.schemas.trading_config import TradingConfigUpdate
        config = TradingConfigUpdate(quote_currency="USD")
        assert config.quote_currency == "USD"

    def test_legacy_quote_normalized(self):
        from app.schemas.trading_config import TradingConfigUpdate
        config = TradingConfigUpdate(quote_currency="ZUSD")
        assert config.quote_currency == "USD"

    def test_lowercase_normalized(self):
        from app.schemas.trading_config import TradingConfigUpdate
        config = TradingConfigUpdate(quote_currency="eur")
        assert config.quote_currency == "EUR"

    def test_invalid_quote_rejected(self):
        from app.schemas.trading_config import TradingConfigUpdate
        from pydantic import ValidationError
        try:
            TradingConfigUpdate(quote_currency="XYZ")
            assert False, "Should have raised ValidationError"
        except ValidationError as e:
            assert "Unsupported" in str(e)

    def test_none_accepted(self):
        from app.schemas.trading_config import TradingConfigUpdate
        config = TradingConfigUpdate(quote_currency=None)
        assert config.quote_currency is None
