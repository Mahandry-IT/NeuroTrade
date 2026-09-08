"""Service trading_engine — orchestration décision → exécution ordres.

Règles métier couvertes :
- RG-2 : limite de gain
- RG-3 : limite de perte (PRIORITAIRE sur RG-9)
- RG-4 : décision basée sur analyse technique
- RG-6 : arrêt immédiat = plus aucune action
- RG-8 : quota mensuel de trades
- RG-9 : durée minimale de détention
- RG-10 : idempotence sur exécution d'ordres
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.modules.trading_config.repository import TradingConfigRepository, BotStateRepository
from app.modules.trading_config.models import BotStatus
from app.modules.trading_engine.repository import PositionRepository, TradeRepository
from app.modules.trading_engine.models import TradeType, PositionStatus
from app.modules.market_analysis.service import MarketAnalysisService
from app.modules.market_scanner.service import MarketScannerService
from app.modules.tax_tracking.repository import TaxTrackingRepository
from app.modules.notifications.service import NotificationService

logger = logging.getLogger(__name__)


def should_force_sell(
    position_opened_at: datetime,
    entry_price: float,
    current_price: float,
    loss_limit_pct: float,
    min_holding_duration: int,
    max_trades_per_month: Optional[int] = None,
    current_month_trades: int = 0,
) -> tuple[bool, str]:
    """Fonction pure — détermine si une position doit être vendue en priorité.

    Priorité stricte : RG-3 (perte) > RG-9 (durée détention) > RG-8 (quota).
    RG-3 s'applique MÊME si la durée min de détention n'est pas écoulée.
    """
    now = datetime.now(timezone.utc)
    pnl_pct = ((current_price - entry_price) / entry_price) * 100 if entry_price > 0 else 0

    # RG-3 : stop-loss — PRIORITAIRE, même avant durée min
    if pnl_pct <= loss_limit_pct:
        return True, f"RG-3: loss {pnl_pct:.1f}% <= limit {loss_limit_pct}%"

    # RG-9 : durée minimale de détention
    holding_minutes = (now - position_opened_at).total_seconds() / 60
    if holding_minutes < min_holding_duration:
        return False, f"RG-9: holding {holding_minutes:.0f}min < min {min_holding_duration}min"

    # RG-8 : quota mensuel atteint — vente autorisée mais signalée
    if max_trades_per_month and current_month_trades >= max_trades_per_month:
        return True, f"RG-8: monthly quota {current_month_trades}/{max_trades_per_month} reached"

    return False, "no_force_sell"


class TradingEngineService:
    def __init__(self, db: Session, executor=None, kraken_client=None):
        self.config_repo = TradingConfigRepository(db)
        self.bot_repo = BotStateRepository(db)
        self.position_repo = PositionRepository(db)
        self.trade_repo = TradeRepository(db)
        self.tax_repo = TaxTrackingRepository(db)
        self.market_service = MarketAnalysisService(db, kraken_client=kraken_client)
        self.notification_service = NotificationService(db)
        self.db = db
        self._executor = executor
        self._kraken_client = kraken_client

    def run_analysis_cycle(self, user_id: int) -> None:
        """Cycle complet d'analyse — appelé par le scheduler."""
        # Vérifier RG-6 : bot toujours actif
        bot_state = self.bot_repo.get_by_user(user_id)
        if not bot_state or bot_state.status != BotStatus.RUNNING:
            logger.info("bot_not_running user_id=%d — skipping cycle", user_id)
            return

        config = self.config_repo.get_or_create(user_id)

        # Mettre à jour le timestamp du dernier cycle
        self.bot_repo.update_last_cycle(user_id)

        # Analyser les positions ouvertes (toutes paires)
        open_positions = self.position_repo.get_open_positions(user_id)
        for position in open_positions:
            self._evaluate_position(user_id, position, config)

        # Auto-ouverture : mode auto-discover OU paire fixe
        if config.auto_discover_markets:
            self._scan_and_open_positions(user_id, config, open_positions)
        else:
            # Mode legacy : paire unique configurée
            pair = config.kraken_pair
            has_position_for_pair = any(p.symbol == pair for p in open_positions)
            if not has_position_for_pair:
                self._try_open_new_position(user_id, config)

        logger.info(
            "analysis_cycle_complete user_id=%d open_positions=%d",
            user_id, len(open_positions),
        )

    def _scan_and_open_positions(
        self, user_id: int, config, open_positions: list
    ) -> None:
        """Scanne les marchés et ouvre des positions sur les meilleurs candidats.

        Algorithme :
        1. Scanner les paires par score de profitabilité (MarketScannerService)
        2. Filtrer celles où on a déjà une position ouverte
        3. Pour chaque candidat restant, analyser le signal technique
        4. Si BUY → vérifier RG-8 → exécuter l'achat
        5. S'arrêter quand les slots sont pleins
        """
        open_count = len(open_positions)
        slots_available = config.max_concurrent_positions - open_count
        if slots_available <= 0:
            logger.info(
                "all_slots_filled user_id=%d open=%d max=%d",
                user_id, open_count, config.max_concurrent_positions,
            )
            return

        if not self._kraken_client:
            logger.warning("no_kraken_client user_id=%d — cannot scan markets", user_id)
            return

        # Scanner les meilleurs candidats
        scanner = MarketScannerService(self._kraken_client)
        candidates = scanner.scan(
            quote_currency=config.quote_currency,
            top_n=config.max_concurrent_positions + 5,  # buffer pour filtrage
            min_volume_24h=config.min_volume_24h,
            cache_ttl=config.scanner_cache_ttl,
        )

        if not candidates:
            logger.info("scanner_no_candidates user_id=%d", user_id)
            return

        # Filtrer les paires où on a déjà une position
        open_symbols = {p.symbol for p in open_positions}
        new_candidates = [c for c in candidates if c.pair not in open_symbols]

        logger.info(
            "scan_result user_id=%d total=%d open_pairs=%d new_candidates=%d slots=%d",
            user_id, len(candidates), len(open_symbols), len(new_candidates), slots_available,
        )

        opened_this_cycle = 0
        for candidate in new_candidates:
            if opened_this_cycle >= slots_available:
                break

            # RG-8 : vérifier quota avant chaque ouverture
            monthly_trades = self.trade_repo.count_monthly_trades(user_id, config.simulation_mode)
            if config.max_trades_per_month and monthly_trades >= config.max_trades_per_month:
                logger.warning(
                    "monthly_quota_reached user_id=%d quota=%d — scan stopped",
                    user_id, config.max_trades_per_month,
                )
                break

            opened = self._try_open_position_for_pair(user_id, config, candidate.pair)
            if opened:
                opened_this_cycle += 1

        if opened_this_cycle > 0:
            logger.info(
                "scan_opened_positions user_id=%d count=%d",
                user_id, opened_this_cycle,
            )

    def _try_open_position_for_pair(
        self, user_id: int, config, pair: str
    ) -> bool:
        """Tente d'ouvrir une position sur une paire spécifique (mode auto-discover).

        Returns:
            True si une position a été ouverte, False sinon.
        """
        logger.info("try_open_position user_id=%d pair=%s (auto-discover)", user_id, pair)

        # Récupérer le prix actuel
        current_price = self.market_service.get_current_price(pair)
        if current_price is None:
            logger.warning("price_unavailable user_id=%d pair=%s", user_id, pair)
            return False

        # Récupérer les prix historiques pour les indicateurs
        prices = self.market_service.get_real_prices(pair, count=100)
        if not prices:
            prices = [current_price]

        # RG-4 : analyse technique + décision
        analysis = self.market_service.analyze(pair, prices)
        signal = analysis.get("signal", "HOLD")
        source = analysis.get("source", "unknown")
        logger.info(
            "market_analysis user_id=%d pair=%s signal=%s source=%s",
            user_id, pair, signal, source,
        )

        if "BUY" not in str(signal).upper():
            return False

        # Vérifier qu'un executor est disponible
        if not self._executor:
            logger.warning("no_executor user_id=%d — cannot execute buy", user_id)
            return False

        # Calculer le montant à investir
        amount_fiat = config.capital_pct_per_trade

        # Exécuter l'achat
        exec_result = self._executor.buy(pair, amount_fiat)
        if not exec_result.success:
            logger.error(
                "buy_execution_failed user_id=%d pair=%s error=%s",
                user_id, pair, exec_result.error_message,
            )
            return False

        # Créer la position en DB
        position = self.position_repo.create(
            user_id=user_id,
            symbol=pair,
            amount=amount_fiat,
            quantity=exec_result.quantity,
            entry_price=exec_result.fill_price,
            is_simulated=config.simulation_mode,
        )
        logger.info(
            "position_opened user_id=%d position_id=%d pair=%s qty=%.8f price=%.2f",
            user_id, position.id, pair, exec_result.quantity, exec_result.fill_price,
        )

        # Enregistrer le trade BUY
        self._record_buy(user_id, position, exec_result, config)

        logger.info(
            "new_position_created user_id=%d pair=%s amount=%.2f price=%.2f signal=%s",
            user_id, pair, amount_fiat, exec_result.fill_price, signal,
        )
        return True

    def _try_open_new_position(self, user_id: int, config) -> None:
        """Tente d'ouvrir une nouvelle position si le signal est BUY (RG-4).

        Algorithme :
        1. Récupérer le prix actuel via KrakenSpotClient (public)
        2. Récupérer les prix historiques OHLC pour les indicateurs
        3. Lancer l'analyse technique (indicateurs + Gemini/fallback)
        4. Si signal BUY → vérifier RG-8 → executor.buy() → créer Position + Trade
        5. Sinon → logger et attendre le prochain cycle
        """
        pair = config.kraken_pair
        logger.info("try_open_position user_id=%d pair=%s", user_id, pair)

        # Récupérer le prix actuel
        current_price = self.market_service.get_current_price(pair)
        if current_price is None:
            logger.warning("price_unavailable user_id=%d pair=%s — cannot open", user_id, pair)
            return

        # Récupérer les prix historiques pour les indicateurs techniques
        prices = self.market_service.get_real_prices(pair, count=100)
        if not prices:
            logger.warning("no_historical_prices user_id=%d pair=%s", user_id, pair)
            prices = [current_price]

        # RG-4 : analyse technique + décision
        analysis = self.market_service.analyze(pair, prices)
        signal = analysis.get("signal", "HOLD")
        source = analysis.get("source", "unknown")
        logger.info(
            "market_analysis user_id=%d pair=%s signal=%s source=%s",
            user_id, pair, signal, source,
        )

        if "BUY" not in str(signal).upper():
            logger.info("no_buy_signal user_id=%d signal=%s — waiting", user_id, signal)
            return

        # RG-8 : vérifier quota mensuel avant achat
        monthly_trades = self.trade_repo.count_monthly_trades(user_id, config.simulation_mode)
        if config.max_trades_per_month and monthly_trades >= config.max_trades_per_month:
            logger.warning(
                "monthly_quota_reached user_id=%d quota=%d — buy blocked",
                user_id, config.max_trades_per_month,
            )
            return

        # Vérifier qu'un executor est disponible
        if not self._executor:
            logger.warning("no_executor user_id=%d — cannot execute buy", user_id)
            return

        # Calculer le montant à investir (capital_pct_per_trade = % du capital)
        amount_fiat = config.capital_pct_per_trade

        # Exécuter l'achat via l'executor (simulation ou réel)
        exec_result = self._executor.buy(pair, amount_fiat)
        if not exec_result.success:
            logger.error(
                "buy_execution_failed user_id=%d pair=%s error=%s",
                user_id, pair, exec_result.error_message,
            )
            return

        # Créer la position en DB
        position = self.position_repo.create(
            user_id=user_id,
            symbol=pair,
            amount=amount_fiat,
            quantity=exec_result.quantity,
            entry_price=exec_result.fill_price,
            is_simulated=config.simulation_mode,
        )
        logger.info(
            "position_opened user_id=%d position_id=%d pair=%s qty=%.8f price=%.2f",
            user_id, position.id, pair, exec_result.quantity, exec_result.fill_price,
        )

        # Enregistrer le trade BUY (RG-10 : idempotence)
        self._record_buy(user_id, position, exec_result, config)

        logger.info(
            "new_position_created user_id=%d pair=%s amount=%.2f price=%.2f signal=%s",
            user_id, pair, amount_fiat, exec_result.fill_price, signal,
        )

    def _evaluate_position(self, user_id: int, position, config) -> None:
        """Évalue une position ouverte et décide de l'action."""
        # Récupérer le prix réel via le symbole de la position (supporte multi-paires)
        current_price = self.market_service.get_current_price(position.symbol)
        if current_price is None:
            # Fallback: prix d'entrée (pas d'appel réseau possible)
            logger.warning("price_unavailable user_id=%d symbol=%s — using entry_price", user_id, position.symbol)
            current_price = position.entry_price

        monthly_trades = self.trade_repo.count_monthly_trades(user_id, config.simulation_mode)

        # Vérifier les garde-fous
        force_sell, reason = should_force_sell(
            position_opened_at=position.opened_at,
            entry_price=position.entry_price,
            current_price=current_price,
            loss_limit_pct=config.loss_limit_pct,
            min_holding_duration=config.min_holding_duration,
            max_trades_per_month=config.max_trades_per_month,
            current_month_trades=monthly_trades,
        )

        if force_sell:
            self._execute_sell(user_id, position, current_price, reason, config)
            return

        # RG-4 : analyse technique + décision
        analysis = self.market_service.analyze(position.symbol, [current_price])
        signal = analysis.get("signal", "HOLD")

        if "BUY" in str(signal).upper():
            logger.info("buy_signal user_id=%d symbol=%s", user_id, position.symbol)
            # RG-8 : vérifier quota avant achat
            if config.max_trades_per_month and monthly_trades >= config.max_trades_per_month:
                logger.warning("monthly_quota_reached user_id=%d quota=%d", user_id, config.max_trades_per_month)
            elif self._executor:
                amount_fiat = position.amount * config.capital_pct_per_trade / 100
                exec_result = self._executor.buy(position.symbol, amount_fiat)
                if exec_result.success:
                    self._record_buy(user_id, position, exec_result, config)
        elif "SELL" in str(signal).upper():
            self._execute_sell(
                user_id, position, current_price,
                f"signal: {signal}", config
            )

    def _execute_sell(
        self, user_id: int, position, price: float, reason: str, config
    ) -> None:
        """Exécute une vente — idempotent via clé (RG-10)."""
        idempotency_key = f"{position.id}_{datetime.now(timezone.utc).isoformat()}"

        # RG-10 : vérifier l'idempotence
        if self.trade_repo.check_idempotency(idempotency_key):
            logger.warning("duplicate_trade_blocked key=%s", idempotency_key)
            return

        # Exécuter via l'executor (simulation ou réel) — supporte multi-paires
        fee = 0.0
        if self._executor:
            exec_result = self._executor.sell(position.symbol, position.quantity, price)
            if not exec_result.success:
                logger.error("sell_execution_failed user_id=%d error=%s", user_id, exec_result.error_message)
                return
            fee = exec_result.fee

        # Calculer le PnL net des frais
        gross_pnl = (price - position.entry_price) * position.quantity
        pnl = gross_pnl - fee

        # Créer le trade avec frais
        trade = self.trade_repo.create(
            user_id=user_id,
            position_id=position.id,
            trade_type=TradeType.SELL,
            symbol=position.symbol,
            amount_fiat=pnl,
            quantity=position.quantity,
            price=price,
            is_simulated=config.simulation_mode,
            idempotency_key=idempotency_key,
            notes=reason,
            fee=fee,
        )

        # Fermer la position
        self.position_repo.close(position.id)

        # RG-11 : enregistrer la conversion taxable si applicable
        if pnl > 0 and not config.simulation_mode:
            self.tax_repo.record_conversion(user_id, trade.id, pnl)

        # Notification
        self.notification_service.send_trade_notification(user_id, trade)

        logger.info(
            "trade_executed user_id=%d trade_id=%d symbol=%s pnl=%.2f reason=%s",
            user_id, trade.id, position.symbol, pnl, reason,
        )

    def _record_buy(
        self, user_id: int, position, exec_result, config
    ) -> None:
        """Enregistre un achat exécuté (RG-10)."""
        idempotency_key = f"buy_{position.id}_{datetime.now(timezone.utc).isoformat()}"

        if self.trade_repo.check_idempotency(idempotency_key):
            logger.warning("duplicate_buy_blocked key=%s", idempotency_key)
            return

        self.trade_repo.create(
            user_id=user_id,
            position_id=position.id,
            trade_type=TradeType.BUY,
            symbol=position.symbol,
            amount_fiat=exec_result.fill_price * exec_result.quantity,
            quantity=exec_result.quantity,
            price=exec_result.fill_price,
            is_simulated=exec_result.is_simulated,
            idempotency_key=idempotency_key,
            notes="signal: BUY",
            fee=exec_result.fee,
        )

    def open_position(
        self, user_id: int, symbol: str, amount_fiat: float,
        price: float, is_simulated: bool = True
    ) -> dict:
        """Ouvre une nouvelle position (usage manuel)."""
        quantity = amount_fiat / price if price > 0 else 0
        position = self.position_repo.create(
            user_id=user_id, symbol=symbol, amount=amount_fiat,
            quantity=quantity, entry_price=price, is_simulated=is_simulated,
        )
        return {
            "id": position.id,
            "symbol": symbol,
            "amount": amount_fiat,
            "entry_price": price,
        }
