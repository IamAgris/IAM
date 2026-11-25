"""HTTP middleware for IAM's backend API."""

from app.api.middleware.auth_middleware import AuthMiddleware

__all__ = ["AuthMiddleware"]
