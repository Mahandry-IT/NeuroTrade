"""Tests simulation — bascule simulation/réel (RG-5)."""


class TestSimulationEndpoints:
    def test_simulation_default_active(self, client, auth_headers):
        response = client.get("/api/v1/config/trading-params", headers=auth_headers)
        assert response.json()["simulation_mode"] is True

    def test_toggle_requires_confirm(self, client, auth_headers):
        response = client.put(
            "/api/v1/config/simulation-mode",
            json={"simulation_mode": False, "confirm": False},
            headers=auth_headers,
        )
        assert response.status_code == 400
