"""Tests notifications."""


class TestNotificationEndpoints:
    def test_unread_empty(self, client, auth_headers):
        response = client.get("/api/v1/notifications/", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    def test_mark_all_read(self, client, auth_headers):
        response = client.post("/api/v1/notifications/read-all", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["marked_read"] == 0
