"""Business logic services for document processing and management."""

from .auth import AuthService, AuthenticationError

__all__ = ["AuthService", "AuthenticationError"]
