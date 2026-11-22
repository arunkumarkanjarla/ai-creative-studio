from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid

from app.db.database import Base


class VisitorSession(Base):
    __tablename__ = "visitor_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    visitor_id = Column(String, nullable=False, index=True)  # UUID from cookie/localStorage
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    ip_address = Column(String, nullable=False, index=True)
    user_agent = Column(Text, nullable=True)
    browser = Column(String, nullable=True)
    os = Column(String, nullable=True)
    device_type = Column(String, nullable=True)  # desktop|mobile|tablet
    path = Column(String, nullable=True)
    studio = Column(String, nullable=True)  # image|audio|video|null
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('ix_visitor_created', 'created_at'),
        Index('ix_visitor_user_created', 'user_id', 'created_at'),
    )


class LoginSession(Base):
    __tablename__ = "login_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    username_attempted = Column(String, nullable=True)  # For failed attempts
    ip_address = Column(String, nullable=False, index=True)
    user_agent = Column(Text, nullable=True)
    browser = Column(String, nullable=True)
    os = Column(String, nullable=True)
    device_type = Column(String, nullable=True)
    login_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_seen_at = Column(DateTime, nullable=True)
    logout_at = Column(DateTime, nullable=True)
    duration = Column(Integer, nullable=True)  # seconds
    status = Column(String, nullable=False, default="success")  # success|failed|logged_out|expired
    failure_reason = Column(String, nullable=True)
    
    __table_args__ = (
        Index('ix_login_created', 'login_at'),
        Index('ix_login_user_created', 'user_id', 'login_at'),
        Index('ix_login_status', 'status'),
    )


class UsageEvent(Base):
    __tablename__ = "usage_events"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    visitor_id = Column(String, nullable=True, index=True)
    ip_address = Column(String, nullable=False)
    studio = Column(String, nullable=True, index=True)  # image|audio|video
    action = Column(String, nullable=False, index=True)  # preview|generate|download|voice_input
    tool = Column(String, nullable=True)  # text_to_image, face_swap, etc.
    success = Column(Boolean, default=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('ix_usage_created', 'created_at'),
        Index('ix_usage_studio_created', 'studio', 'created_at'),
        Index('ix_usage_action_created', 'action', 'created_at'),
    )
