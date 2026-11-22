"""
Audio Studio models for TTS, STT and voice management.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Text, Float, Index
from sqlalchemy.orm import relationship

from app.db.database import Base


class VoiceProfile(Base):
    """Built-in and custom voice profiles for TTS."""
    __tablename__ = "voice_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # NULL for built-in voices
    visitor_id = Column(String(255), nullable=True, index=True)  # For guest custom voices
    
    name = Column(String(200), nullable=False, index=True)
    voice_id = Column(String(200), nullable=False)  # e.g. "en-US-AriaNeural" or custom ID
    
    # Voice characteristics
    gender = Column(String(20), nullable=True)  # male, female, child
    age_group = Column(String(20), nullable=True)  # adult, child
    language = Column(String(50), nullable=True)  # en-US, hi-IN, te-IN
    locale = Column(String(50), nullable=True)  # Full locale code
    region = Column(String(50), nullable=True, index=True)  # North America, Europe, Asia, etc.
    country = Column(String(100), nullable=True)  # United States, United Kingdom, etc.
    accent = Column(String(100), nullable=True)  # American, British, Australian, etc.
    voice_type = Column(String(50), nullable=True)  # narration, news, cheerful, friendly, etc.
    
    # Custom voice settings (for user-created presets)
    is_custom = Column(Boolean, default=False, index=True)
    base_voice_id = Column(String(200), nullable=True)  # Base voice for custom presets
    pitch = Column(Float, default=1.0)  # Pitch multiplier
    rate = Column(Float, default=1.0)  # Speed multiplier
    volume = Column(Float, default=1.0)  # Volume multiplier
    style = Column(String(50), nullable=True)  # cheerful, sad, etc (if supported)
    
    # Voice cloning (optional)
    cloned_from_file = Column(String(500), nullable=True)  # Path to source audio sample
    
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index('ix_voice_gender_lang', 'gender', 'language'),
        Index('ix_voice_custom_user', 'is_custom', 'user_id'),
    )


class TTSGeneration(Base):
    """Text-to-speech generation history."""
    __tablename__ = "tts_generations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # NULL for guests
    visitor_id = Column(String(255), nullable=True, index=True)  # For guest ownership
    voice_profile_id = Column(Integer, ForeignKey("voice_profiles.id"), nullable=True)
    
    input_text = Column(Text, nullable=False)
    voice_id = Column(String(200), nullable=False)  # Snapshot of voice used
    voice_name = Column(String(200), nullable=True)
    
    # Generation parameters
    pitch = Column(Float, default=1.0)
    rate = Column(Float, default=1.0)
    volume = Column(Float, default=1.0)
    output_format = Column(String(10), default="mp3")  # mp3, wav
    
    # Output
    file_path = Column(String(500), nullable=True)
    file_size_bytes = Column(Integer, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    status = Column(String(20), default="processing", index=True)  # processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('ix_tts_user_created', 'user_id', 'created_at'),
        Index('ix_tts_status', 'status'),
    )


class Transcription(Base):
    """Speech-to-text transcription history."""
    __tablename__ = "transcriptions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # NULL for guests
    visitor_id = Column(String(255), nullable=True, index=True)  # For guest ownership
    
    # Input
    source_file = Column(String(500), nullable=True)  # Uploaded file path
    source_type = Column(String(20), default="upload")  # upload, recording
    
    # Detection/settings
    language = Column(String(50), nullable=True)  # Detected or specified language
    language_detected = Column(String(50), nullable=True)
    duration_seconds = Column(Float, nullable=True)
    
    # Output
    transcript_text = Column(Text, nullable=True)
    segments_json = Column(Text, nullable=True)  # JSON array of timestamped segments
    
    # Export formats
    txt_file = Column(String(500), nullable=True)
    srt_file = Column(String(500), nullable=True)
    
    status = Column(String(20), default="processing", index=True)  # processing, completed, failed
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    
    __table_args__ = (
        Index('ix_transcription_user_created', 'user_id', 'created_at'),
        Index('ix_transcription_status', 'status'),
    )
