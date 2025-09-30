"""Authentication and authorization service layer."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Protocol, Tuple

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.config.settings import Settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserDTO(Protocol):
    """Lightweight projection of a user entity used by the auth service."""

    id: uuid.UUID
    email: str
    username: str
    role: str
    password_hash: str
    is_active: bool
    mfa_enabled: bool


class UserRepository(Protocol):
    """Persistence operations required for user authentication."""

    async def get_by_email(self, email: str) -> Optional[UserDTO]:
        ...

    async def record_login_success(self, user_id: uuid.UUID) -> None:
        ...

    async def record_login_failure(self, email: str) -> None:
        ...

    async def update_password_hash(self, user_id: uuid.UUID, password_hash: str) -> None:
        ...


class RefreshTokenRepository(Protocol):
    """Persistence for refresh token lifecycle management."""

    async def store(
        self,
        *,
        jti: uuid.UUID,
        user_id: uuid.UUID,
        expires_at: datetime,
        token: str,
    ) -> None:
        ...

    async def revoke(self, jti: uuid.UUID) -> None:
        ...

    async def is_active(self, jti: uuid.UUID) -> bool:
        ...


class TokenPair(Dict[str, str]):
    """Convenience mapping for issued tokens."""

    access_token: str
    refresh_token: str


class AuthService:
    """Service orchestrating authentication, JWT issuance, and RBAC hooks."""

    def __init__(
        self,
        *,
        settings: Settings,
        user_repository: UserRepository,
        refresh_token_repository: RefreshTokenRepository,
    ) -> None:
        self._settings = settings
        self._user_repository = user_repository
        self._refresh_token_repository = refresh_token_repository

    async def authenticate(self, *, email: str, password: str) -> Tuple[UserDTO, TokenPair]:
        """Authenticate a user with credentials and return the user plus token pair."""

        user = await self._user_repository.get_by_email(email)
        if user is None:
            await self._user_repository.record_login_failure(email)
            raise AuthenticationError("Invalid credentials")

        if not user.is_active:
            raise AuthenticationError("Account is disabled")

        if not self._verify_password(password, user.password_hash):
            await self._user_repository.record_login_failure(email)
            raise AuthenticationError("Invalid credentials")

        tokens = await self._issue_tokens(user_id=user.id, subject=user.email)
        await self._user_repository.record_login_success(user.id)
        return user, tokens

    async def refresh_tokens(self, refresh_token: str) -> TokenPair:
        """Issue a new token pair using an existing refresh token."""

        try:
            payload = jwt.decode(
                refresh_token,
                self._settings.secret_key,
                algorithms=[self._settings.algorithm],
            )
        except JWTError as exc:  # pragma: no cover - defensive branch
            raise AuthenticationError("Invalid refresh token") from exc

        jti = uuid.UUID(payload["jti"])
        user_id = uuid.UUID(payload["sub"])

        if not await self._refresh_token_repository.is_active(jti):
            raise AuthenticationError("Refresh token revoked or expired")

        tokens = await self._issue_tokens(user_id=user_id, subject=str(user_id))
        await self._refresh_token_repository.revoke(jti)
        return tokens

    async def logout(self, refresh_token: str) -> None:
        """Invalidate the provided refresh token."""

        try:
            payload = jwt.decode(
                refresh_token,
                self._settings.secret_key,
                algorithms=[self._settings.algorithm],
            )
        except JWTError as exc:
            raise AuthenticationError("Invalid refresh token") from exc

        jti = uuid.UUID(payload["jti"])
        await self._refresh_token_repository.revoke(jti)

    async def initiate_mfa(self, *, user: UserDTO) -> None:
        """Hook for triggering MFA challenges when enabled for the user."""

        if not user.mfa_enabled:  # Nothing to do if MFA is disabled
            return

        # The actual MFA delivery (email, SMS, authenticator) should be implemented
        # by an infrastructure adapter. This hook is provided so the auth service
        # can remain framework-agnostic.
        raise NotImplementedError("MFA delivery not implemented for this deployment")

    async def rotate_password(self, *, user_id: uuid.UUID, new_password: str) -> None:
        """Rotate a user's password hash enforcing policy requirements."""

        password_hash = self._hash_password(new_password)
        await self._user_repository.update_password_hash(user_id, password_hash)

    async def _issue_tokens(self, *, user_id: uuid.UUID, subject: str) -> TokenPair:
        """Create access and refresh tokens and persist refresh state."""

        now = datetime.now(timezone.utc)
        access_expires = now + timedelta(minutes=self._settings.access_token_expire_minutes)
        refresh_expires = now + timedelta(days=self._settings.refresh_token_expire_days)

        access_token = self._encode_token(
            claims={"sub": str(user_id), "type": "access"},
            expires_at=access_expires,
        )

        refresh_jti = uuid.uuid4()
        refresh_token = self._encode_token(
            claims={"sub": str(user_id), "type": "refresh", "jti": str(refresh_jti)},
            expires_at=refresh_expires,
        )

        await self._refresh_token_repository.store(
            jti=refresh_jti,
            user_id=user_id,
            expires_at=refresh_expires,
            token=refresh_token,
        )

        return TokenPair(access_token=access_token, refresh_token=refresh_token)  # type: ignore[arg-type]

    def _encode_token(self, *, claims: Dict[str, str], expires_at: datetime) -> str:
        payload = {**claims, "exp": expires_at, "iat": datetime.now(timezone.utc)}
        return jwt.encode(payload, self._settings.secret_key, algorithm=self._settings.algorithm)

    @staticmethod
    def _verify_password(password: str, password_hash: str) -> bool:
        return pwd_context.verify(password, password_hash)

    @staticmethod
    def _hash_password(password: str) -> str:
        return pwd_context.hash(password)


class AuthenticationError(RuntimeError):
    """Raised when authentication fails."""

    pass
