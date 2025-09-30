"""Authentication and authorization schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Credentials required for user login."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    device_fingerprint: Optional[str] = Field(
        default=None, description="Opaque device identifier for risk analysis"
    )


class RefreshTokenRequest(BaseModel):
    """Refresh token payload."""

    refresh_token: str


class AuthTokens(BaseModel):
    """Issued tokens for the client."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token TTL in seconds")
    refresh_expires_in: int = Field(
        ..., description="Refresh token TTL in seconds"
    )


class AuthUser(BaseModel):
    """Authenticated user context returned to the client."""

    id: str
    email: EmailStr
    username: str
    role: str
    last_login: Optional[datetime] = None
    mfa_enabled: bool = False


class AuthResponse(BaseModel):
    """Response payload for successful authentication."""

    tokens: AuthTokens
    user: AuthUser


class LogoutResponse(BaseModel):
    """Response confirming logout action."""

    success: bool = True
    message: str = "Successfully logged out"
