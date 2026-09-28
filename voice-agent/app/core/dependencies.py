"""FastAPI Dependency injection helpers and authentication guards."""

import logging
from typing import Optional
from urllib.parse import urlparse

from fastapi import Header, HTTPException, WebSocket, WebSocketException, status
from app.auth.models import AuthUser
from app.auth.clerk import clerk_verifier
from app.core.config import Settings, settings

logger = logging.getLogger(__name__)


def get_settings() -> Settings:
    """Dependency provider for application settings."""
    return settings


def _extract_token(
    authorization: Optional[str] = None,
) -> Optional[str]:
    """Extract a Clerk session token from an Authorization header."""
    if authorization:
        parts = authorization.strip().split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    return None


def get_current_user(
    authorization: Optional[str] = Header(None),
) -> AuthUser:
    """Enforce authentication on protected HTTP routes, extracting verified user identity."""
    token = _extract_token(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid session token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = clerk_verifier.verify_token(token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token. Please re-authenticate.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_optional_user(
    authorization: Optional[str] = Header(None),
) -> Optional[AuthUser]:
    """Optional authentication resolver for routes supporting guest or pre-login discovery."""
    token = _extract_token(authorization)
    if not token:
        return None
    return clerk_verifier.verify_token(token)


def is_allowed_origin(origin_header: Optional[str]) -> bool:
    """Validate WebSocket origin against allowed local and production hosts (Finding F01/F07)."""
    if not origin_header:
        # Direct non-browser clients or test runners without origin header
        return True

    try:
        parsed = urlparse(origin_header)
        hostname = (parsed.hostname or "").lower()
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "testserver"):
            return True
        # Check against server host setting
        if hostname == (settings.server_host or "").lower():
            return True
        return False
    except Exception:
        return False


def validate_ws_auth(
    websocket: WebSocket,
    token: Optional[str] = None,
) -> AuthUser:
    """Validate WebSocket handshake Origin and authenticate the connecting user."""
    # 1. Validate Origin header
    origin = websocket.headers.get("origin")
    if not is_allowed_origin(origin):
        logger.warning(f"Rejected WebSocket connection from unauthorized origin: {origin}")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Unauthorized origin")

    # 2. API tests and non-browser clients can use a bearer header. Browser
    # clients supply the negotiated subprotocol token at the route boundary.
    auth_token = token
    if not auth_token:
        auth_header = websocket.headers.get("authorization")
        auth_token = _extract_token(auth_header)

    if not auth_token:
        logger.warning("Rejected WebSocket connection: missing authentication token")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication token required")

    user = clerk_verifier.verify_token(auth_token)
    if not user:
        logger.warning("Rejected WebSocket connection: invalid or expired token")
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid or expired token")

    return user
