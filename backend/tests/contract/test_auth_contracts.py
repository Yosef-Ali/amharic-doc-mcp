"""Contract tests for authentication endpoints."""

from __future__ import annotations

import pytest

@pytest.mark.contract
class TestAuthContracts:
    """Ensure auth endpoints satisfy OpenAPI contract semantics."""

    @pytest.mark.asyncio
    async def test_login_success(self, async_client, valid_user_credentials):
        """POST /auth/login returns tokens and user profile on success."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={
                "email": valid_user_credentials.email,
                "password": valid_user_credentials.password,
            },
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["tokens"]["token_type"] == "bearer"
        assert payload["user"]["email"] == valid_user_credentials.email

    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, async_client):
        """Invalid credentials yield 401 according to the contract."""
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "unknown@example.com", "password": "bad-pass"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_requires_valid_token(self, async_client, issued_refresh_token):
        """POST /auth/refresh returns new tokens when refresh token is valid."""
        response = await async_client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {issued_refresh_token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert "access_token" in payload["tokens"]

    @pytest.mark.asyncio
    async def test_logout_invalidates_refresh_token(self, async_client, issued_refresh_token):
        """POST /auth/logout acknowledges token revocation."""
        response = await async_client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {issued_refresh_token}"},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
