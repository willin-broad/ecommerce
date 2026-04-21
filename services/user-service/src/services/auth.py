from datetime import timedelta
from typing import Optional

from fastapi import HTTPException, status
from jose import JWTError, jwt
import bcrypt
import hashlib

from ..config import get_settings
from ..utils import utcnow

settings = get_settings()


def _pre_hash(secret: str) -> bytes:
    """Pre-hash with SHA-256 to bypass bcrypt's 72-byte limit."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest().encode("utf-8")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of the given plaintext password."""
    return bcrypt.hashpw(_pre_hash(plain), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Return True if plaintext matches the bcrypt hash."""
    try:
        return bcrypt.checkpw(_pre_hash(plain), hashed.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a short-lived JWT access token.
    Embeds `type=access` to prevent refresh tokens from being used as access tokens.
    """
    to_encode = data.copy()
    expire = utcnow() + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    Create a long-lived JWT refresh token.
    Embeds `type=refresh` so it cannot be used as an access token.
    """
    to_encode = data.copy()
    expire = utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict:
    """
    Decode and validate a JWT token.
    Raises HTTP 401 on any decoding failure (expired, tampered, etc.).
    """
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
