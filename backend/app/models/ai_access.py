from sqlalchemy import (
    BigInteger, Boolean, CheckConstraint, Column,
    DateTime, ForeignKey, Integer, String, Text,
    text, select, func
)
from sqlalchemy.dialects.postgresql import INET
from app.db.database import Base


class AIStudioAccessSetting(Base):
    __tablename__ = "ai_studio_access_settings"

    id = Column(BigInteger, primary_key=True)
    studio = Column(String(20), nullable=False, unique=True)

    guest_access_enabled = Column(Boolean, nullable=False, default=True)
    guest_generation_limit = Column(Integer, nullable=False, default=3)
    guest_limit_period = Column(String(20), nullable=False, default="day")

    authenticated_limit_enabled = Column(
        Boolean, nullable=False, default=False
    )
    authenticated_generation_limit = Column(Integer, nullable=True)

    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class AIGenerationAttempt(Base):
    __tablename__ = "ai_generation_attempts"

    id = Column(BigInteger, primary_key=True)

    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    visitor_id = Column(String(64), nullable=True)
    studio = Column(String(20), nullable=False)

    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    prompt = Column(Text, nullable=True)

    status = Column(String(30), nullable=False, default="started")
    error_message = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    completed_at = Column(DateTime(timezone=True), nullable=True)