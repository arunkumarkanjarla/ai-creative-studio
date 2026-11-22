"""Refresh token sessions for persistent login."""
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
    text,
)

from app.db.database import Base


class RefreshToken(Base):
    """Hashed refresh token row; one row per active device session."""

    __tablename__ = "refresh_tokens"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # SHA-256 hex of the opaque refresh token
    token_hash = Column(String(64), nullable=False, unique=True, index=True)

    # Tokens that rotate together share a family; reuse of a revoked token
    # revokes the entire family.
    family_id = Column(String(64), nullable=False, index=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)

    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)

    revoked = Column(Boolean, nullable=False, default=False, index=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revoked_reason = Column(String(64), nullable=True)

    # Previous token in the rotation chain (for audit / reuse detection)
    replaced_by_id = Column(Integer, nullable=True)

    __table_args__ = (
        Index("ix_refresh_tokens_user_active", "user_id", "revoked", "expires_at"),
        Index("ix_refresh_tokens_family", "family_id", "revoked"),
    )
