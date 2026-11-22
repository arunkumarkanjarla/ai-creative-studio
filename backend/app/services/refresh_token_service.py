"""Create, rotate, and revoke refresh tokens."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.core.security import (
    generate_refresh_token,
    hash_refresh_token,
    new_refresh_family_id,
    refresh_token_expiry,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User


class RefreshTokenError(Exception):
    def __init__(self, message: str, *, revoke_family: bool = False, family_id: str | None = None):
        super().__init__(message)
        self.message = message
        self.revoke_family = revoke_family
        self.family_id = family_id


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def issue_refresh_token(
    db: Session,
    user_id: int,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
    family_id: str | None = None,
) -> tuple[str, RefreshToken]:
    """Create a new refresh token row and return (plaintext, row)."""
    plaintext = generate_refresh_token()
    row = RefreshToken(
        user_id=user_id,
        token_hash=hash_refresh_token(plaintext),
        family_id=family_id or new_refresh_family_id(),
        created_at=_utcnow(),
        last_used_at=_utcnow(),
        expires_at=refresh_token_expiry(),
        user_agent=user_agent,
        ip_address=ip_address,
        revoked=False,
    )
    db.add(row)
    db.flush()
    return plaintext, row


def revoke_token_row(
    db: Session,
    row: RefreshToken,
    *,
    reason: str = "logout",
) -> None:
    if row.revoked:
        return
    row.revoked = True
    row.revoked_at = _utcnow()
    row.revoked_reason = reason


def revoke_family(
    db: Session,
    family_id: str,
    *,
    reason: str = "reuse_detected",
) -> int:
    now = _utcnow()
    rows = (
        db.query(RefreshToken)
        .filter(
            RefreshToken.family_id == family_id,
            RefreshToken.revoked.is_(False),
        )
        .all()
    )
    for row in rows:
        row.revoked = True
        row.revoked_at = now
        row.revoked_reason = reason
    return len(rows)


def revoke_user_tokens(
    db: Session,
    user_id: int,
    *,
    reason: str = "logout_all",
    except_token_hash: str | None = None,
) -> int:
    now = _utcnow()
    q = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked.is_(False),
    )
    if except_token_hash:
        q = q.filter(RefreshToken.token_hash != except_token_hash)
    rows = q.all()
    for row in rows:
        row.revoked = True
        row.revoked_at = now
        row.revoked_reason = reason
    return len(rows)


def revoke_by_plaintext(
    db: Session,
    plaintext: str | None,
    *,
    reason: str = "logout",
) -> bool:
    if not plaintext:
        return False
    token_hash = hash_refresh_token(plaintext)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if not row:
        return False
    revoke_token_row(db, row, reason=reason)
    return True


def rotate_refresh_token(
    db: Session,
    plaintext: str,
    *,
    user_agent: str | None = None,
    ip_address: str | None = None,
) -> tuple[User, str, RefreshToken]:
    """
    Validate refresh token, rotate it (sliding expiry), return (user, new_plaintext, row).

    Reuse of a revoked token revokes the entire family and raises RefreshTokenError.
    Disabled/deleted users are rejected.
    """
    if not plaintext:
        raise RefreshTokenError("Missing refresh token")

    token_hash = hash_refresh_token(plaintext)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if not row:
        raise RefreshTokenError("Invalid refresh token")

    now = _utcnow()

    # Token reuse detection: presented a token that was already rotated/revoked
    if row.revoked:
        revoke_family(db, row.family_id, reason="reuse_detected")
        db.commit()
        raise RefreshTokenError(
            "Refresh token reuse detected",
            revoke_family=True,
            family_id=row.family_id,
        )

    expires = row.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < now:
        revoke_token_row(db, row, reason="expired")
        db.commit()
        raise RefreshTokenError("Refresh token expired")

    user = db.query(User).filter(User.id == row.user_id).first()
    if not user or not user.is_active:
        revoke_family(db, row.family_id, reason="user_inactive")
        db.commit()
        raise RefreshTokenError("User inactive or deleted")

    # Rotate: revoke old, issue new in same family with sliding expiry
    new_plaintext, new_row = issue_refresh_token(
        db,
        user.id,
        user_agent=user_agent or row.user_agent,
        ip_address=ip_address or row.ip_address,
        family_id=row.family_id,
    )
    revoke_token_row(db, row, reason="rotated")
    row.replaced_by_id = new_row.id
    row.last_used_at = now
    new_row.last_used_at = now
    db.flush()
    return user, new_plaintext, new_row
