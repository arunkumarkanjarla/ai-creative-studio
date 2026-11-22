
from datetime import datetime, timedelta, timezone
import hashlib
import secrets

import jwt

from pwdlib import PasswordHash

from app.core.config import settings


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str
) -> bool:

    return password_hash.verify(
        plain_password,
        hashed_password
    )


def create_access_token(user_id: int) -> str:

    now = datetime.now(timezone.utc)
    expire = now + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "type": "access",
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM
    )


def access_token_expires_in_seconds() -> int:
    return int(settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)


def decode_token(token: str) -> dict:
    """Decode and verify JWT token. Returns payload or raises exception."""
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )


def generate_refresh_token() -> str:
    """Opaque refresh token (never store plaintext; hash before persist)."""
    return secrets.token_urlsafe(48)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_refresh_family_id() -> str:
    return secrets.token_urlsafe(24)


def refresh_token_expiry(from_time: datetime | None = None) -> datetime:
    base = from_time or datetime.now(timezone.utc)
    if base.tzinfo is None:
        base = base.replace(tzinfo=timezone.utc)
    return base + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
