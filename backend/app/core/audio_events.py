"""
Audio Event Logging
"""
import time
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import Request
from user_agents import parse

from app.models.audio_events import AudioEvent
from app.core.analytics import get_client_ip


def log_audio_event(
    db: Session,
    request: Request,
    action: str,
    user_id: Optional[int] = None,
    visitor_id: Optional[str] = None,
    voice_id: Optional[str] = None,
    voice_name: Optional[str] = None,
    language: Optional[str] = None,
    text_length: Optional[int] = None,
    input_text: Optional[str] = None,
    audio_duration: Optional[float] = None,
    file_size: Optional[int] = None,
    processing_time_ms: Optional[int] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    generation_id: Optional[int] = None,
    transcription_id: Optional[int] = None,
):
    """Log an audio event to the database"""
    try:
        # Parse user agent
        forwarded_for = request.headers.get("X-Forwarded-For")
        ip = get_client_ip(request, forwarded_for)
        
        user_agent_string = request.headers.get("User-Agent", "")
        user_agent = parse(user_agent_string)
        
        browser = user_agent.browser.family if user_agent.browser else None
        os = user_agent.os.family if user_agent.os else None
        device = user_agent.device.family if user_agent.device and user_agent.device.family != "Other" else None
        
        # Get visitor ID from header if not provided
        if not visitor_id:
            visitor_id = request.headers.get("X-Visitor-Id")
        
        event = AudioEvent(
            user_id=user_id,
            visitor_id=visitor_id,
            ip_address=ip,
            user_agent=user_agent_string[:500] if user_agent_string else None,
            browser=browser,
            os=os,
            device=device,
            action=action,
            studio="audio",
            voice_id=voice_id,
            voice_name=voice_name,
            language=language,
            text_length=text_length,
            input_text=input_text[:1000] if input_text else None,  # Limit stored text
            audio_duration=audio_duration,
            file_size=file_size,
            processing_time_ms=processing_time_ms,
            status=status,
            error_message=error_message[:500] if error_message else None,
            generation_id=generation_id,
            transcription_id=transcription_id,
        )
        
        db.add(event)
        db.commit()
        
    except Exception as e:
        print(f"Failed to log audio event: {str(e)}")
        # Don't fail the main operation if logging fails
        pass


def check_rate_limit(db: Session, visitor_id: str, ip: str, limit_per_hour: int = 100) -> bool:
    """
    Check if a guest has exceeded their rate limit.
    Returns True if limit exceeded, False otherwise.
    """
    from datetime import datetime, timedelta
    
    hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    # Count events in the last hour for this visitor or IP
    count = db.query(AudioEvent).filter(
        AudioEvent.created_at >= hour_ago,
        AudioEvent.user_id == None,  # Only check guests
        (
            (AudioEvent.visitor_id == visitor_id) |
            (AudioEvent.ip_address == ip)
        ),
        AudioEvent.action.in_(["generate", "transcribe"])  # Only count generation actions
    ).count()
    
    return count >= limit_per_hour
