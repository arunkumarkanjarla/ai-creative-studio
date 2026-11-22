"""
Video Studio models: projects, scenes, characters, and generation jobs.
"""
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from app.db.database import Base


class VideoProject(Base):
    """A video generation job / project."""

    __tablename__ = "video_projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    prompt = Column(Text, nullable=False)
    category = Column(String(50), nullable=False, default="custom", index=True)
    length_preset = Column(String(20), nullable=False, default="short")
    duration_seconds = Column(Float, nullable=True)
    orientation = Column(String(20), nullable=False, default="portrait")
    resolution = Column(String(20), nullable=False, default="720p")
    fps = Column(Integer, nullable=False, default=24)
    audio_mode = Column(String(30), nullable=False, default="dialogue")
    subtitles = Column(Boolean, nullable=False, default=True)
    output_format = Column(String(10), nullable=False, default="mp4")
    engine = Column(String(40), nullable=False, default="local", index=True)

    status = Column(String(20), nullable=False, default="queued", index=True)
    progress = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)

    output_path = Column(String(500), nullable=True)
    thumbnail_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)

    queue_started_at = Column(DateTime, nullable=True)
    processing_started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    generation_time_seconds = Column(Float, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    scenes = relationship(
        "VideoScene",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="VideoScene.scene_index",
    )
    characters = relationship(
        "VideoCharacter",
        back_populates="project",
        cascade="all, delete-orphan",
        order_by="VideoCharacter.character_index",
    )

    __table_args__ = (
        Index("ix_video_projects_user_created", "user_id", "created_at"),
        Index("ix_video_projects_status_created", "status", "created_at"),
    )


class VideoScene(Base):
    """A scene within a video project."""

    __tablename__ = "video_scenes"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scene_index = Column(Integer, nullable=False, default=0)
    prompt = Column(Text, nullable=True)
    dialogue_text = Column(Text, nullable=True)
    character_name = Column(String(200), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    # Optional per-scene background / plate image
    image_path = Column(String(500), nullable=True)

    project = relationship("VideoProject", back_populates="scenes")


class VideoCharacter(Base):
    """A character role with image and assigned voice."""

    __tablename__ = "video_characters"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(
        Integer, ForeignKey("video_projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    character_index = Column(Integer, nullable=False, default=0)
    name = Column(String(200), nullable=False)
    voice_id = Column(String(200), nullable=True)
    image_path = Column(String(500), nullable=True)

    project = relationship("VideoProject", back_populates="characters")
