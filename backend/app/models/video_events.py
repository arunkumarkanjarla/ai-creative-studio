"""
Video Events — detailed tracking of all video studio operations.
"""
from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import INET, JSONB

from app.db.database import Base


class VideoEvent(Base):
    """Track video-related events for analytics and admin monitoring."""

    __tablename__ = "video_events"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    ip_address = Column(INET, nullable=True)
    user_agent = Column(Text, nullable=True)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    device = Column(String(100), nullable=True)

    action = Column(String(50), nullable=False, index=True)
    studio = Column(String(20), nullable=False, default="video")
    details = Column(JSONB, nullable=True)

    status = Column(String(20), nullable=False, default="success", index=True)
    error_message = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)

    project_id = Column(Integer, nullable=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    def __repr__(self):
        return (
            f"<VideoEvent(id={self.id}, action={self.action}, "
            f"user_id={self.user_id}, project_id={self.project_id})>"
        )
