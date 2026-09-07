"""Tests unitaires trading_engine — règles métier pures."""

from datetime import datetime, timedelta, timezone

from app.modules.trading_engine.service import should_force_sell


class TestShouldForceSell:
    """Fonction pure — testable indépendamment de la DB."""

    def test_rg3_loss_limit_triggers_sell(self):
        """RG-3 : perte atteint la limite → vente FORCÉE même si durée min pas écoulée."""
        opened = datetime.now(timezone.utc) - timedelta(minutes=5)  # très récent
        force, reason = should_force_sell(
            position_opened_at=opened,
            entry_price=100.0,
            current_price=96.0,  # -4%
            loss_limit_pct=-3.0,
            min_holding_duration=60,
        )
        assert force is True
        assert "RG-3" in reason

    def test_rg3_priority_over_rg9(self):
        """RG-3 est PRIORITAIRE sur RG-9 — vente même si durée min pas écoulée."""
        opened = datetime.now(timezone.utc) - timedelta(minutes=1)  # 1 min seulement
        force, reason = should_force_sell(
            position_opened_at=opened,
            entry_price=200.0,
            current_price=190.0,  # -5%
            loss_limit_pct=-3.0,
            min_holding_duration=60,
        )
        assert force is True
        assert "RG-3" in reason

    def test_rg9_holding_too_short_no_sell(self):
        """RG-9 : durée min pas écoulée ET pas de perte → pas de vente."""
        opened = datetime.now(timezone.utc) - timedelta(minutes=30)
        force, reason = should_force_sell(
            position_opened_at=opened,
            entry_price=100.0,
            current_price=101.0,  # +1%
            loss_limit_pct=-3.0,
            min_holding_duration=60,
        )
        assert force is False
        assert "RG-9" in reason

    def test_rg9_holding_sufficient_allows_sell(self):
        """RG-9 : durée suffisante + pas de perte → pas de force sell."""
        opened = datetime.now(timezone.utc) - timedelta(minutes=120)
        force, reason = should_force_sell(
            position_opened_at=opened,
            entry_price=100.0,
            current_price=102.0,  # +2%
            loss_limit_pct=-3.0,
            min_holding_duration=60,
        )
        assert force is False
        assert "no_force_sell" in reason

    def test_rg8_quota_reached_forces_sell(self):
        """RG-8 : quota mensuel atteint → vente signalée (si durée OK)."""
        opened = datetime.now(timezone.utc) - timedelta(minutes=120)
        force, reason = should_force_sell(
            position_opened_at=opened,
            entry_price=100.0,
            current_price=102.0,
            loss_limit_pct=-3.0,
            min_holding_duration=60,
            max_trades_per_month=20,
            current_month_trades=20,
        )
        assert force is True
        assert "RG-8" in reason

    def test_rg8_quota_not_reached_no_sell(self):
        """RG-8 : quota pas atteint → pas de force sell."""
        opened = datetime.now(timezone.utc) - timedelta(minutes=120)
        force, reason = should_force_sell(
            position_opened_at=opened,
            entry_price=100.0,
            current_price=102.0,
            loss_limit_pct=-3.0,
            min_holding_duration=60,
            max_trades_per_month=20,
            current_month_trades=10,
        )
        assert force is False

    def test_gain_limit_not_triggers_sell(self):
        """RG-2 : gain positif mais sous la limite → pas de vente forcée."""
        opened = datetime.now(timezone.utc) - timedelta(minutes=120)
        force, reason = should_force_sell(
            position_opened_at=opened,
            entry_price=100.0,
            current_price=104.0,  # +4% < 5% limit
            loss_limit_pct=-3.0,
            min_holding_duration=60,
        )
        assert force is False

    def test_edge_case_zero_entry_price(self):
        """Cas limite : prix d'entrée = 0 → pas de division par zéro."""
        opened = datetime.now(timezone.utc) - timedelta(minutes=120)
        force, _ = should_force_sell(
            position_opened_at=opened,
            entry_price=0.0,
            current_price=100.0,
            loss_limit_pct=-3.0,
            min_holding_duration=60,
        )
        assert isinstance(force, bool)
