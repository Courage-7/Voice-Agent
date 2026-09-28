"""Authentication module exposing Clerk-verified application identities."""

from app.auth.clerk import clerk_verifier
from app.auth.models import AuthUser

__all__ = [
    "AuthUser",
    "clerk_verifier",
]
