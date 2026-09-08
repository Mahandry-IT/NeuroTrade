"""Exécuteurs d'ordres — interface commune pour simuler ou exécuter réellement.

TradingEngineService reçoit un OrderExecutor injecté selon TradingConfig.mode.
SimulatedExecutor lit le prix réel via KrakenSpotClient (public), écrit un
Trade(is_simulated=True). N'appelle jamais AddOrder.
RealExecutor appelle KrakenSpotClient.add_order() (privé, signé).
Écrit Trade(is_simulated=False).

Les deux appliquent une estimation de frais Kraken (~0.26% taker)
pour que les stats de simulation restent réalistes.
"""

import logging
from typing import Protocol

from app.modules.kraken.client import KrakenSpotClient, TAKER_FEE_RATE
from app.modules.kraken.schemas import ExecutionResult

logger = logging.getLogger(__name__)


class OrderExecutor(Protocol):
    """Interface commune pour l'exécution d'ordres."""

    def buy(self, pair: str, amount_fiat: float) -> ExecutionResult: ...
    def sell(self, pair: str, quantity: float, current_price: float) -> ExecutionResult: ...


class SimulatedExecutor:
    """Exécution simulée — lit le prix réel, écrit en DB, n'appelle jamais AddOrder.

    Applique une estimation de frais (Kraken taker fee ~0.26%)
    pour que les stats de simulation restent réalistes.
    """

    def __init__(self, client: KrakenSpotClient, trade_repo, user_id: int):
        self._client = client
        self._trade_repo = trade_repo
        self._user_id = user_id

    def buy(self, pair: str, amount_fiat: float) -> ExecutionResult:
        """Simule un achat — calcule la quantité au prix réel."""
        ticker = self._client.get_ticker_price(pair)
        if not ticker:
            return ExecutionResult(
                success=False, is_simulated=True,
                error_message="Unable to fetch price from Kraken",
            )

        price = ticker.ask  # buy at ask
        fee = amount_fiat * TAKER_FEE_RATE
        net_amount = amount_fiat - fee
        quantity = net_amount / price if price > 0 else 0

        logger.info(
            "simulated_buy pair=%s amount_fiat=%.2f price=%.2f qty=%.8f fee=%.4f",
            pair, amount_fiat, price, quantity, fee,
        )
        return ExecutionResult(
            success=True,
            fill_price=price,
            quantity=quantity,
            fee=fee,
            is_simulated=True,
        )

    def sell(self, pair: str, quantity: float, current_price: float) -> ExecutionResult:
        """Simule une vente — calcule le PnL au prix réel."""
        gross = quantity * current_price
        fee = gross * TAKER_FEE_RATE
        net = gross - fee

        logger.info(
            "simulated_sell pair=%s qty=%.8f price=%.2f gross=%.2f fee=%.4f net=%.2f",
            pair, quantity, current_price, gross, fee, net,
        )
        return ExecutionResult(
            success=True,
            fill_price=current_price,
            quantity=quantity,
            fee=fee,
            is_simulated=True,
        )


class RealExecutor:
    """Exécution réelle — appelle KrakenSpotClient.add_order() (privé, signé).

    ⚠️ N'est utilisé QUE si TradingConfig.simulation_mode = False.
    """

    def __init__(self, client: KrakenSpotClient):
        self._client = client

    def buy(self, pair: str, amount_fiat: float) -> ExecutionResult:
        """Place un ordre d'achat réel sur Kraken."""
        ticker = self._client.get_ticker_price(pair)
        if not ticker:
            return ExecutionResult(
                success=False, is_simulated=False,
                error_message="Unable to fetch price from Kraken",
            )

        # Pour un achat au market, on calcule le volume en base
        price = ticker.ask
        volume = amount_fiat / price if price > 0 else 0

        try:
            result = self._client.add_order(
                pair=pair, side="buy", order_type="market",
                volume=volume, reduce_only=False,
            )
            return ExecutionResult(
                success=True,
                order_id=result.order_id,
                fill_price=price,
                quantity=volume,
                fee=amount_fiat * TAKER_FEE_RATE,
                is_simulated=False,
            )
        except Exception as e:
            logger.error("kraken_buy_error pair=%s error=%s", pair, str(e))
            return ExecutionResult(
                success=False, is_simulated=False,
                error_message=str(e),
            )

    def sell(self, pair: str, quantity: float, current_price: float) -> ExecutionResult:
        """Place un ordre de vente réel sur Kraken."""
        try:
            result = self._client.add_order(
                pair=pair, side="sell", order_type="market",
                volume=quantity, reduce_only=True,
            )
            gross = quantity * current_price
            fee = gross * TAKER_FEE_RATE
            return ExecutionResult(
                success=True,
                order_id=result.order_id,
                fill_price=current_price,
                quantity=quantity,
                fee=fee,
                is_simulated=False,
            )
        except Exception as e:
            logger.error("kraken_sell_error pair=%s error=%s", pair, str(e))
            return ExecutionResult(
                success=False, is_simulated=False,
                error_message=str(e),
            )
