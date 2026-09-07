"""Tests trading_config — paramètres de trading + contrôle bot."""


class TestTradingConfigEndpoints:
    """Tests d'intégration des endpoints config."""

    def test_get_default_config(self, client, auth_headers):
        response = client.get("/api/v1/config/trading-params", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["simulation_mode"] is True  # RG-5 : activé par défaut
        assert data["gain_limit_pct"] == 5.0
        assert data["loss_limit_pct"] == -3.0

    def test_update_config(self, client, auth_headers):
        response = client.put(
            "/api/v1/config/trading-params",
            json={"gain_limit_pct": 10.0, "max_trades_per_month": 30},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["gain_limit_pct"] == 10.0
        assert response.json()["max_trades_per_month"] == 30

    def test_update_config_invalid_value(self, client, auth_headers):
        response = client.put(
            "/api/v1/config/trading-params",
            json={"capital_pct_per_trade": 150.0},  # > 100
            headers=auth_headers,
        )
        assert response.status_code == 422  # validation error

    def test_update_config_empty(self, client, auth_headers):
        response = client.put(
            "/api/v1/config/trading-params",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 400  # no fields

    def test_simulation_mode_requires_confirm(self, client, auth_headers):
        # Sans confirmation → refusé
        response = client.put(
            "/api/v1/config/simulation-mode",
            json={"simulation_mode": False, "confirm": False},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_simulation_mode_with_confirm(self, client, auth_headers):
        response = client.put(
            "/api/v1/config/simulation-mode",
            json={"simulation_mode": False, "confirm": True},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert "REAL" in response.json()["message"]

    def test_bot_status_default_stopped(self, client, auth_headers):
        response = client.get("/api/v1/bot/status", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"

    def test_bot_start_without_platform_fails(self, client, auth_headers):
        response = client.post("/api/v1/bot/start", headers=auth_headers)
        assert response.status_code == 400
        assert "not connected" in response.json()["detail"]

    def test_bot_stop(self, client, auth_headers):
        response = client.post("/api/v1/bot/stop", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["status"] == "stopped"
