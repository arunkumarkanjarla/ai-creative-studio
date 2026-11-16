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


class GeneratedVideo(Base):
    __tablename__ = "generated_videos"

    id = Column(BigInteger, primary_key=True, index=True)

    user_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    visitor_id = Column(String(64), nullable=True, index=True)

    prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True)
    model_name = Column(String(150), nullable=True)
    video_path = Column(Text, nullable=True)
    thumbnail_path = Column(Text, nullable=True)
    video_width = Column(Integer, nullable=True)
    video_height = Column(Integer, nullable=True)
    video_format = Column(String(20), nullable=True)
    duration_seconds = Column(Numeric(10, 2), nullable=True)

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
