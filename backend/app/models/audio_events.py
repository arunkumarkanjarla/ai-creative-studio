"""
Audio Events - Detailed tracking of all audio operations
"""
from sqlalchemy import Column, Integer, String, DateTime, Float, Boolean, Text, ForeignKey
from sqlalchemy.dialects.postgresql import INET
from datetime import datetime
from app.db.database import Base


class AudioEvent(Base):
    """Track all audio-related events for analytics and admin monitoring"""
    __tablename__ = "audio_events"

    id = Column(Integer, primary_key=True, index=True)
    
    # User identification
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    visitor_id = Column(String(255), nullable=True, index=True)
    ip_address = Column(INET, nullable=True)
    
    # Request metadata
    user_agent = Column(Text, nullable=True)
    browser = Column(String(100), nullable=True)
    os = Column(String(100), nullable=True)
    device = Column(String(100), nullable=True)
    
    # Event details
    action = Column(String(50), nullable=False, index=True)  # generate, play, download, transcribe, etc.
    studio = Column(String(20), nullable=False, default="audio")  # audio
    
    # Audio/Voice details
    voice_id = Column(String(100), nullable=True)
    voice_name = Column(String(255), nullable=True)
    language = Column(String(10), nullable=True)
    
    # Content details
    text_length = Column(Integer, nullable=True)
    input_text = Column(Text, nullable=True)  # For TTS
    audio_duration = Column(Float, nullable=True)
    file_size = Column(Integer, nullable=True)
    
    # Processing details
    processing_time_ms = Column(Integer, nullable=True)
    status = Column(String(20), nullable=False, index=True)  # success, failed, rate_limited
    error_message = Column(Text, nullable=True)
    
    # Reference IDs
    generation_id = Column(Integer, nullable=True)  # TTS generation ID
    transcription_id = Column(Integer, nullable=True)  # STT transcription ID
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<AudioEvent(id={self.id}, action={self.action}, user_id={self.user_id}, visitor_id={self.visitor_id})>"
