"""Tests tax_tracking — compteurs fiscaux + export CSV."""


class TestTaxTrackingEndpoints:
    def test_counters_default(self, client, auth_headers):
        response = client.get("/api/v1/tax/counters", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["monthly_trade_count"] == 0
        assert data["alert_reached"] is False

    def test_export_empty(self, client, auth_headers):
        response = client.get("/api/v1/tax/export", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["rows"] == []
        assert data["total_amount_fiat"] == 0.0
