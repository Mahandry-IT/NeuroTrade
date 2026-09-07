"""Tests history — pagination + stats."""


class TestHistoryEndpoints:
    def test_trades_empty(self, client, auth_headers):
        response = client.get("/api/v1/history/trades", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["data"] == []
        assert data["meta"]["total"] == 0

    def test_stats_empty(self, client, auth_headers):
        response = client.get("/api/v1/history/stats", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["total_trades"] == 0

    def test_trades_pagination(self, client, auth_headers):
        response = client.get(
            "/api/v1/history/trades?page=2&limit=10",
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["meta"]["page"] == 2
