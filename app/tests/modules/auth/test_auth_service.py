"""Tests auth — register, login, JWT, platform connect."""

import pytest


class TestAuthEndpoints:
    """Tests d'intégration des endpoints auth."""

    def test_register_success(self, client):
        response = client.post("/api/v1/auth/register", json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "password123",
        })
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"

    def test_register_duplicate_username(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "dupuser",
            "email": "dup@example.com",
            "password": "password123",
        })
        response = client.post("/api/v1/auth/register", json={
            "username": "dupuser",
            "email": "other@example.com",
            "password": "password123",
        })
        assert response.status_code == 409

    def test_login_success(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "loginuser",
            "email": "login@example.com",
            "password": "password123",
        })
        response = client.post("/api/v1/auth/login", json={
            "username": "loginuser",
            "password": "password123",
        })
        assert response.status_code == 200
        assert "access_token" in response.json()

    def test_login_wrong_password(self, client):
        client.post("/api/v1/auth/register", json={
            "username": "wrongpw",
            "email": "wrongpw@example.com",
            "password": "password123",
        })
        response = client.post("/api/v1/auth/login", json={
            "username": "wrongpw",
            "password": "wrongpassword",
        })
        assert response.status_code == 401

    def test_platform_connect(self, client, auth_headers):
        response = client.post(
            "/api/v1/auth/platform-connect",
            json={
                "platform_name": "binance",
                "api_key": "test-api-key",
                "api_secret": "test-api-secret",
            },
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "connected"

    def test_platform_status(self, client, auth_headers):
        # Connect d'abord
        client.post(
            "/api/v1/auth/platform-connect",
            json={
                "platform_name": "binance",
                "api_key": "key",
                "api_secret": "secret",
            },
            headers=auth_headers,
        )
        response = client.get("/api/v1/auth/platform-status", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["platform_name"] == "binance"

    def test_unauthorized_access(self, client):
        response = client.get("/api/v1/config/trading-params")
        assert response.status_code == 403  # no auth header


class TestDTOValidation:
    """Tests de validation des DTOs (bornes explicites)."""

    def test_register_short_password(self, client):
        response = client.post("/api/v1/auth/register", json={
            "username": "test",
            "email": "test@example.com",
            "password": "short",
        })
        assert response.status_code == 422  # password < 8 chars

    def test_register_invalid_email(self, client):
        response = client.post("/api/v1/auth/register", json={
            "username": "test",
            "email": "not-an-email",
            "password": "password123",
        })
        assert response.status_code == 422
