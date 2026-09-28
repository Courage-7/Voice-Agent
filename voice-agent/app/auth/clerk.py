"""Clerk session-token verification for FastAPI routes and WebSockets."""

import base64
import json
import logging
from typing import Any, Optional

import jwt

from app.auth.models import AuthUser
from app.core.config import settings

logger = logging.getLogger(__name__)


class ClerkTokenVerifier:
    """Verify Clerk RS256 session JWTs against the configured JWKS or PEM key."""

    def __init__(self) -> None:
        self._jwks_client: Optional[jwt.PyJWKClient] = None
        self._jwks_url: Optional[str] = None

    def _get_jwks_client(self) -> jwt.PyJWKClient:
        jwks_url = settings.clerk_jwks_url.strip()
        if not jwks_url:
            raise ValueError("CLERK_JWKS_URL is not configured")
        if self._jwks_client is None or self._jwks_url != jwks_url:
            self._jwks_client = jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=300)
            self._jwks_url = jwks_url
        return self._jwks_client

    def verify_token(self, token: str) -> Optional[AuthUser]:
        """Return the Clerk subject only when signature and claims are valid."""
        if settings.environment == "testing" and token.startswith("test."):
            return self._verify_test_token(token)
        if not token or not settings.clerk_issuer.strip():
            return None
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") != "RS256":
                return None
            signing_key: Any = settings.clerk_jwt_key or self._get_jwks_client().get_signing_key_from_jwt(token).key
            payload = jwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                issuer=settings.clerk_issuer,
                options={"require": ["sub", "exp", "iat", "nbf"], "verify_aud": False},
            )
            authorized_parties = {party.strip() for party in settings.clerk_authorized_parties.split(",") if party.strip()}
            if authorized_parties and payload.get("azp") not in authorized_parties:
                logger.warning("Rejected Clerk token with an unauthorized azp claim")
                return None
            subject = payload.get("sub")
            return AuthUser(id=subject, email=str(payload.get("email") or "")) if isinstance(subject, str) and subject else None
        except (jwt.InvalidTokenError, ValueError, TypeError) as exc:
            logger.info("Rejected Clerk session token: %s", exc)
            return None

    @staticmethod
    def _verify_test_token(token: str) -> Optional[AuthUser]:
        """Decode explicit test-only identities; never enabled outside pytest."""
        try:
            encoded = token.split(".", 1)[1]
            payload = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)).decode("utf-8"))
            subject = payload["sub"]
            return AuthUser(id=subject, email=str(payload.get("email") or "")) if isinstance(subject, str) and subject else None
        except (KeyError, TypeError, ValueError, UnicodeDecodeError):
            return None


def create_test_token(user_id: str, email: str = "") -> str:
    """Create a test-only credential for isolated API tests."""
    if settings.environment != "testing":
        raise RuntimeError("Test tokens are unavailable outside the testing environment")
    payload = json.dumps({"sub": user_id, "email": email}, separators=(",", ":")).encode("utf-8")
    return "test." + base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


clerk_verifier = ClerkTokenVerifier()
