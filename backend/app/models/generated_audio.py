from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from app.db.database import Base


class GeneratedAudio(Base):
    __tablename__ = "generated_audios"

    id = Column(BigInteger, primary_key=True, index=True)

    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    visitor_id = Column(String(64), nullable=True, index=True)

    prompt = Column(Text, nullable=False)
    model_name = Column(String(150), nullable=True)
    audio_path = Column(Text, nullable=True)
    audio_format = Column(String(20), nullable=True)
    duration_seconds = Column(Numeric(10, 2), nullable=True)
    sample_rate = Column(Integer, nullable=True)

    status = Column(String(30), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    generation_time_seconds = Column(Numeric(10, 2), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
