"""Client Kraken Spot — appels HTTP bruts (public + privé).

Endpoints publics : Ticker, AssetPairs, OHLC, Time, Depth — utilisés
pour le prix réel en simulation ET pour les indicateurs techniques.
Endpoints privés : Balance, AddOrder, QueryOrders, ClosedOrders —
utilisés uniquement en mode réel (HMAC-SHA512 signé).

Base URL : https://api.kraken.com (pas de bascule sandbox — le mode
simulation est une différence applicatif, pas d'URL).
"""

import hashlib
import hmac
import logging
import time
import urllib.parse
from base64 import b64decode, b64encode
from typing import Optional

import httpx

from app.core.security import decrypt_api_key
from app.modules.kraken.nonce import get_nonce
from app.modules.kraken.schemas import (
    KrakenAssetPair, KrakenBalance, KrakenOHLC, KrakenTickerPrice,
    KrakenAddOrderResult, KrakenError,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.kraken.com"
TAKER_FEE_RATE = 0.0026  # Kraken default taker fee ~0.26%


class KrakenAPIError(Exception):
    """Erreur retournée par l'API Kraken."""
    def __init__(self, errors: list[str]):
        self.errors = errors
        super().__init__(f"Kraken API error: {errors}")


class KrakenSpotClient:
    """Client HTTP pour l'API Kraken Spot.

    Args:
        api_key_encrypted: clé API Kraken chiffrée (Fernet), ou None pour endpoints publics.
        api_secret_encrypted: clé secrète Kraken chiffrée (Fernet), ou None pour endpoints publics.
        timeout: timeout HTTP en secondes.
    """

    def __init__(
        self,
        api_key_encrypted: Optional[str] = None,
        api_secret_encrypted: Optional[str] = None,
        timeout: float = 10.0,
    ):
        self._api_key_encrypted = api_key_encrypted
        self._api_secret_encrypted = api_secret_encrypted
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)

    # ── Public endpoints ──

    def get_time(self) -> dict:
        """GET /0/public/Time — vérifie la connectivité (pas d'auth)."""
        return self._public_get("Time")

    def get_asset_pairs(self) -> dict[str, dict]:
        """GET /0/public/AssetPairs — métadonnées de toutes les paires."""
        data = self._public_get("AssetPairs")
        return data.get("result", {})

    def get_ticker(self, pair: str) -> dict:
        """GET /0/public/Ticker — prix actuel (bid/ask/last)."""
        data = self._public_get("Ticker", {"pair": pair})
        result = data.get("result", {})
        # Kraken retourne une clé dynamique (ex: "XXBTZUSD")
        for key, val in result.items():
            return {"symbol": key, **val}
        return {}

    def get_ticker_price(self, pair: str) -> Optional[KrakenTickerPrice]:
        """Retourne le prix actuel sous forme de DTO."""
        raw = self.get_ticker(pair)
        if not raw:
            return None
        return KrakenTickerPrice(
            symbol=raw.get("symbol", pair),
            bid=float(raw.get("b", [0])[0]),
            ask=float(raw.get("a", [0])[0]),
            last_price=float(raw.get("c", [0])[0]),
            volume_24h=float(raw.get("v", [0, 0])[1]),
        )

    def get_ohlc(self, pair: str, interval: int = 60, since: Optional[int] = None) -> list[KrakenOHLC]:
        """GET /0/public/OHLC — données de bougies.

        Args:
            pair: symbole de la paire (ex: "XXBTZUSD").
            interval: intervalle en minutes (1, 5, 15, 30, 60, 240, 1440, 10080, 21600).
            since: timestamp Unix (optionnel, filtre les bougies après ce timestamp).
        """
        params = {"pair": pair, "interval": interval}
        if since:
            params["since"] = since
        data = self._public_get("OHLC", params)
        result = data.get("result", {})
        for key, candles in result.items():
            if key == "last":
                continue
            return [
                KrakenOHLC(
                    time=c[0], open=c[1], high=c[2], low=c[3],
                    close=c[4], vwap=c[5], volume=c[6], count=int(c[7]),
                )
                for c in candles
            ]
        return []

    def get_depth(self, pair: str, count: int = 10) -> dict:
        """GET /0/public/Depth — carnet d'ordres."""
        return self._public_get("Depth", {"pair": pair, "count": count})

    # ── Private endpoints ──

    def get_balance(self) -> list[KrakenBalance]:
        """GET /0/private/Balance — soldes de tous les actifs (privé)."""
        data = self._private_post("Balance")
        result = data.get("result", {})
        balances = []
        for asset, balance_str in result.items():
            if asset == "result" or asset.startswith("result"):
                continue
            balances.append(KrakenBalance(
                asset=asset, balance=float(balance_str),
            ))
        return balances

    def add_order(
        self,
        pair: str,
        side: str,
        order_type: str,
        volume: float,
        price: Optional[float] = None,
        reduce_only: bool = False,
        validate: bool = False,
    ) -> KrakenAddOrderResult:
        """POST /0/private/AddOrder — place un ordre (privé).

        Args:
            pair: paire de trading (ex: "XXBTZUSD").
            side: "buy" ou "sell".
            order_type: type d'ordre (ex: "market", "limit").
            volume: quantité à acheter/vendre.
            price: prix limite (requis pour order_type="limit").
            reduce_only: si True, réduit uniquement une position existante.
            validate: si True, valide seulement sans exécuter (dry run Kraken).
        """
        params: dict = {
            "pair": pair,
            "type": side,
            "ordertype": order_type,
            "volume": str(volume),
        }
        if price is not None:
            params["price"] = str(price)
        if reduce_only:
            params["reduce_only"] = "true"
        if validate:
            params["validate"] = "true"

        data = self._private_post("AddOrder", params)
        result = data.get("result", {})
        txid = result.get("txid", [])
        order_id = txid[0] if txid else ""
        return KrakenAddOrderResult(
            order_id=order_id,
            descr=result.get("descr", {}),
        )

    def query_orders(self, order_ids: str) -> dict:
        """POST /0/private/QueryOrders — état d'ordres (privé)."""
        data = self._private_post("QueryOrders", {"txid": order_ids})
        return data.get("result", {})

    def get_closed_orders(self, start: Optional[int] = None) -> dict:
        """POST /0/private/ClosedOrders — historique ordres fermés."""
        params: dict = {}
        if start:
            params["start"] = start
        data = self._private_post("ClosedOrders", params)
        return data.get("result", {})

    # ── Private helpers ──

    def _public_get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Appel GET vers /0/public/{endpoint}."""
        url = f"{BASE_URL}/0/public/{endpoint}"
        try:
            resp = self._client.get(url, params=params or {})
            resp.raise_for_status()
            data = resp.json()
            errors = data.get("error", [])
            if errors:
                raise KrakenAPIError(errors)
            return data
        except httpx.HTTPError as e:
            logger.error("kraken_public_get_error endpoint=%s error=%s", endpoint, str(e))
            raise

    def _private_post(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Appel POST vers /0/private/{endpoint} avec signature HMAC-SHA512."""
        if not self._api_key_encrypted or not self._api_secret_encrypted:
            raise ValueError("Kraken API key/secret required for private endpoints")

        api_key = decrypt_api_key(self._api_key_encrypted)
        api_secret = decrypt_api_key(self._api_secret_encrypted)
        nonce = str(get_nonce())

        post_data = params or {}
        post_data["nonce"] = nonce

        encoded = urllib.parse.urlencode(post_data).encode()
        message = (nonce.encode() + encoded)
        sha256 = hashlib.sha256(message).digest()
        mac = hmac.new(
            b64decode(api_secret), b"/0/private/" + endpoint.encode() + sha256, hashlib.sha512
        )
        signature = b64encode(mac.digest()).decode()

        headers = {
            "API-Key": api_key,
            "API-Sign": signature,
        }

        url = f"{BASE_URL}/0/private/{endpoint}"
        try:
            resp = self._client.post(url, data=post_data, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            errors = data.get("error", [])
            if errors:
                raise KrakenAPIError(errors)
            return data
        except httpx.HTTPError as e:
            logger.error("kraken_private_post_error endpoint=%s error=%s", endpoint, str(e))
            raise

    def close(self):
        """Ferme le client HTTP."""
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
