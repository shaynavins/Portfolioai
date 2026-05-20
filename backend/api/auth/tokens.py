"""
Token Management — Access & Refresh Tokens
Implements JWT token pairs with secure storage and validation
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
import secrets
import structlog

from api.config import settings

log = structlog.get_logger()


class TokenResponse:
    """Response object for token generation."""
    def __init__(self, access_token: str, refresh_token: str, token_type: str = "bearer"):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_type = token_type

    def to_dict(self):
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
        }


def create_access_token(user_id: str, expires_in_minutes: Optional[int] = None) -> str:
    """
    Create a short-lived JWT access token.
    
    Args:
        user_id: The user's ID
        expires_in_minutes: Override default expiry (default: 15 min)
    
    Returns:
        Encoded JWT token
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_in_minutes or settings.JWT_ACCESS_EXPIRE_MINUTES
    )
    payload = {
        "sub": user_id,
        "type": "access",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_refresh_token(user_id: str, jti: Optional[str] = None) -> str:
    """
    Create a longer-lived JWT refresh token.
    Used to obtain new access tokens without re-authenticating.
    
    Args:
        user_id: The user's ID
        jti: JWT ID (optional, for token revocation tracking)
    
    Returns:
        Encoded JWT token
    """
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.JWT_REFRESH_EXPIRE_DAYS
    )
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "jti": jti or secrets.token_urlsafe(32),  # JWT ID for tracking
    }
    return jwt.encode(
        payload,
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM,
    )


def create_token_pair(user_id: str) -> TokenResponse:
    """
    Create both access and refresh tokens.
    
    Args:
        user_id: The user's ID
    
    Returns:
        TokenResponse with both tokens
    """
    access_token = create_access_token(user_id)
    refresh_token = create_refresh_token(user_id)
    return TokenResponse(access_token, refresh_token)


def verify_access_token(token: str) -> dict:
    """
    Verify and decode an access token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload
    
    Raises:
        JWTError: If token is invalid, expired, or wrong type
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "access":
            raise JWTError("Invalid token type")
        return payload
    except JWTError as e:
        log.warning("Invalid access token", error=str(e))
        raise


def verify_refresh_token(token: str) -> dict:
    """
    Verify and decode a refresh token.
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload
    
    Raises:
        JWTError: If token is invalid, expired, or wrong type
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        if payload.get("type") != "refresh":
            raise JWTError("Invalid token type")
        return payload
    except JWTError as e:
        log.warning("Invalid refresh token", error=str(e))
        raise


def extract_user_id(token: str) -> Optional[str]:
    """
    Extract user ID from a token without full validation.
    Used for informational purposes only.
    """
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return payload.get("sub")
    except JWTError:
        return None
