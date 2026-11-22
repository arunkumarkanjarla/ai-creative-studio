"""
Audio Studio API - Text-to-Speech and Speech-to-Text
"""
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import asyncio
import json
import tempfile
import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.database import get_db
from app.models.user import User
from app.models.audio import VoiceProfile, TTSGeneration, Transcription
from app.api.v1.dependencies import get_current_user, get_optional_user
from app.core.analytics import track_usage_event, get_client_ip
from app.core.audio_events import log_audio_event, check_rate_limit
from fastapi import Request

router = APIRouter(prefix="/audio", tags=["Audio Studio"])

# Audio storage directory
BACKEND_DIR = Path(__file__).resolve().parents[3]
AUDIO_DIR = BACKEND_DIR / "generated_audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# Built-in voice library with edge-tts voices
# https://speech.microsoft.com/portal/voicegallery
BUILTIN_VOICES = [
    # English US - Adult
    {"voice_id": "en-US-AriaNeural", "name": "Aria (US Female)", "gender": "female", "age_group": "adult", "language": "en-US", "locale": "en-US"},
    {"voice_id": "en-US-GuyNeural", "name": "Guy (US Male)", "gender": "male", "age_group": "adult", "language": "en-US", "locale": "en-US"},
    {"voice_id": "en-US-JennyNeural", "name": "Jenny (US Female)", "gender": "female", "age_group": "adult", "language": "en-US", "locale": "en-US"},
    {"voice_id": "en-US-TonyNeural", "name": "Tony (US Male)", "gender": "male", "age_group": "adult", "language": "en-US", "locale": "en-US"},
    
    # English US - Child
    {"voice_id": "en-US-AnaNeural", "name": "Ana (US Child)", "gender": "female", "age_group": "child", "language": "en-US", "locale": "en-US"},
    
    # English India
    {"voice_id": "en-IN-NeerjaNeural", "name": "Neerja (India Female)", "gender": "female", "age_group": "adult", "language": "en-IN", "locale": "en-IN"},
    {"voice_id": "en-IN-PrabhatNeural", "name": "Prabhat (India Male)", "gender": "male", "age_group": "adult", "language": "en-IN", "locale": "en-IN"},
    
    # Hindi
    {"voice_id": "hi-IN-SwaraNeural", "name": "Swara (Hindi Female)", "gender": "female", "age_group": "adult", "language": "hi-IN", "locale": "hi-IN"},
    {"voice_id": "hi-IN-MadhurNeural", "name": "Madhur (Hindi Male)", "gender": "male", "age_group": "adult", "language": "hi-IN", "locale": "hi-IN"},
    
    # Telugu
    {"voice_id": "te-IN-ShrutiNeural", "name": "Shruti (Telugu Female)", "gender": "female", "age_group": "adult", "language": "te-IN", "locale": "te-IN"},
    {"voice_id": "te-IN-MohanNeural", "name": "Mohan (Telugu Male)", "gender": "male", "age_group": "adult", "language": "te-IN", "locale": "te-IN"},
    
    # Child-style presets (higher pitch, faster rate based on female voices)
    {"voice_id": "preset-child-en-IN", "name": "Child-Style (India English)", "gender": "female", "age_group": "child", "language": "en-IN", "locale": "en-IN", "base_voice": "en-IN-NeerjaNeural", "preset_pitch": 1.3, "preset_rate": 1.1},
    {"voice_id": "preset-child-hi-IN", "name": "Child-Style (Hindi)", "gender": "female", "age_group": "child", "language": "hi-IN", "locale": "hi-IN", "base_voice": "hi-IN-SwaraNeural", "preset_pitch": 1.3, "preset_rate": 1.1},
    {"voice_id": "preset-child-te-IN", "name": "Child-Style (Telugu)", "gender": "female", "age_group": "child", "language": "te-IN", "locale": "te-IN", "base_voice": "te-IN-ShrutiNeural", "preset_pitch": 1.3, "preset_rate": 1.1},
    
    # English UK
    {"voice_id": "en-GB-SoniaNeural", "name": "Sonia (UK Female)", "gender": "female", "age_group": "adult", "language": "en-GB", "locale": "en-GB"},
    {"voice_id": "en-GB-RyanNeural", "name": "Ryan (UK Male)", "gender": "male", "age_group": "adult", "language": "en-GB", "locale": "en-GB"},
]


def init_builtin_voices(db: Session):
    """Initialize built-in voice profiles in database if not present."""
    for voice_data in BUILTIN_VOICES:
        existing = db.query(VoiceProfile).filter(
            VoiceProfile.voice_id == voice_data["voice_id"],
            VoiceProfile.is_custom == False
        ).first()
        
        if not existing:
            # For preset voices, use base_voice as the actual voice_id for edge-tts
            base_voice = voice_data.get("base_voice")
            profile = VoiceProfile(
                user_id=None,
                name=voice_data["name"],
                voice_id=voice_data["voice_id"],
                base_voice_id=base_voice,  # For presets, this is the actual edge-tts voice
                gender=voice_data["gender"],
                age_group=voice_data["age_group"],
                language=voice_data["language"],
                locale=voice_data["locale"],
                # Apply preset parameters
                pitch=voice_data.get("preset_pitch", 1.0),
                rate=voice_data.get("preset_rate", 1.0),
                volume=1.0,
                is_custom=False,
                is_active=True
            )
            db.add(profile)
    
    db.commit()


@router.get("/voices")
def list_voices(
    request: Request,
    gender: Optional[str] = Query(None),
    age_group: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    include_custom: bool = Query(True),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """List available voices with optional filters. Works for guests and authenticated users."""
    import time
    start_time = time.time()
    
    # Initialize built-in voices if needed
    init_builtin_voices(db)
    
    query = db.query(VoiceProfile).filter(VoiceProfile.is_active == True)
    
    # Apply filters
    if gender:
        query = query.filter(VoiceProfile.gender == gender)
    if age_group:
        query = query.filter(VoiceProfile.age_group == age_group)
    if language:
        query = query.filter(VoiceProfile.language == language)
    
    # Include built-in voices and user's custom voices (if authenticated)
    if include_custom and current_user:
        query = query.filter(
            (VoiceProfile.is_custom == False) | 
            (VoiceProfile.user_id == current_user.id)
        )
    else:
        query = query.filter(VoiceProfile.is_custom == False)
    
    voices = query.all()
    
    # Log the event
    duration_ms = int((time.time() - start_time) * 1000)
    log_audio_event(
        db=db,
        request=request,
        action="list_voices",
        user_id=current_user.id if current_user else None,
        status="success",
        processing_time_ms=duration_ms
    )
    
    return {
        "voices": [
            {
                "id": v.id,
                "name": v.name,
                "voice_id": v.voice_id,
                "gender": v.gender,
                "age_group": v.age_group,
                "language": v.language,
                "locale": v.locale,
                "is_custom": v.is_custom,
                "pitch": v.pitch if v.is_custom else 1.0,
                "rate": v.rate if v.is_custom else 1.0,
                "volume": v.volume if v.is_custom else 1.0,
            }
            for v in voices
        ]
    }


@router.post("/voices/custom")
def create_custom_voice(
    name: str = Form(...),
    base_voice_id: str = Form(...),
    pitch: float = Form(1.0),
    rate: float = Form(1.0),
    volume: float = Form(1.0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a custom voice preset."""
    # Get base voice info
    base_voice = db.query(VoiceProfile).filter(
        VoiceProfile.voice_id == base_voice_id,
        VoiceProfile.is_custom == False
    ).first()
    
    if not base_voice:
        raise HTTPException(status_code=404, detail="Base voice not found")
    
    custom_voice = VoiceProfile(
        user_id=current_user.id,
        name=name,
        voice_id=f"custom_{current_user.id}_{name.replace(' ', '_').lower()}",
        gender=base_voice.gender,
        age_group=base_voice.age_group,
        language=base_voice.language,
        locale=base_voice.locale,
        is_custom=True,
        base_voice_id=base_voice_id,
        pitch=pitch,
        rate=rate,
        volume=volume,
        is_active=True
    )
    
    db.add(custom_voice)
    db.commit()
    db.refresh(custom_voice)
    
    return {
        "id": custom_voice.id,
        "name": custom_voice.name,
        "voice_id": custom_voice.voice_id,
        "message": "Custom voice created successfully"
    }


@router.post("/generate")
async def generate_tts(
    request: Request,
    text: str = Form(...),
    voice_id: str = Form(...),
    pitch: float = Form(1.0),
    rate: float = Form(1.0),
    volume: float = Form(1.0),
    output_format: str = Form("mp3"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Generate text-to-speech audio. Works for guests and authenticated users."""
    import time
    start_time = time.time()
    
    visitor_id = request.headers.get("X-Visitor-Id")
    forwarded_for = request.headers.get("X-Forwarded-For")
    ip = get_client_ip(request, forwarded_for)
    
    # For guests, check rate limits
    if not current_user:
        if not visitor_id:
            log_audio_event(
                db=db,
                request=request,
                action="generate",
                status="failed",
                error_message="Missing X-Visitor-Id header",
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            raise HTTPException(status_code=400, detail="Visitor ID required for guest access")
        
        if check_rate_limit(db, visitor_id, ip, limit_per_hour=50):
            log_audio_event(
                db=db,
                request=request,
                action="generate",
                visitor_id=visitor_id,
                status="rate_limited",
                error_message="Rate limit exceeded (50 per hour for guests)",
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            raise HTTPException(
                status_code=429, 
                detail="Rate limit exceeded. Please sign in for unlimited access or try again later."
            )
    
    # Validate text length (stricter for guests)
    max_length = 5000 if current_user else 1000
    if len(text) > max_length:
        log_audio_event(
            db=db,
            request=request,
            action="generate",
            user_id=current_user.id if current_user else None,
            visitor_id=visitor_id if not current_user else None,
            text_length=len(text),
            status="failed",
            error_message=f"Text too long (max {max_length} characters)",
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        raise HTTPException(
            status_code=400, 
            detail=f"Text too long (max {max_length} characters for {'users' if current_user else 'guests'})"
        )
    
    # Get voice info
    voice_profile = db.query(VoiceProfile).filter(
        VoiceProfile.voice_id == voice_id
    ).first()
    
    if not voice_profile:
        log_audio_event(
            db=db,
            request=request,
            action="generate",
            user_id=current_user.id if current_user else None,
            visitor_id=visitor_id if not current_user else None,
            voice_id=voice_id,
            text_length=len(text),
            status="failed",
            error_message="Voice not found",
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        raise HTTPException(status_code=404, detail="Voice not found")
    
    # Check if voice is custom and user is not authenticated
    if voice_profile.is_custom and not current_user:
        log_audio_event(
            db=db,
            request=request,
            action="generate",
            visitor_id=visitor_id,
            voice_id=voice_id,
            voice_name=voice_profile.name,
            text_length=len(text),
            status="failed",
            error_message="Custom voices require authentication",
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        raise HTTPException(
            status_code=401, 
            detail="Custom voices are only available to signed-in users. Please sign in to use custom voices."
        )
    
    # Create generation record
    generation = TTSGeneration(
        user_id=current_user.id if current_user else None,
        visitor_id=visitor_id if not current_user else None,
        voice_profile_id=voice_profile.id,
        input_text=text,
        voice_id=voice_id,
        voice_name=voice_profile.name,
        pitch=pitch,
        rate=rate,
        volume=volume,
        output_format=output_format,
        status="processing"
    )
    db.add(generation)
    db.commit()
    db.refresh(generation)
    
    try:
        # Generate audio using edge-tts
        import edge_tts
        
        # Determine actual voice to use
        # Presets and custom voices use base_voice_id, regular voices use voice_id
        actual_voice_id = voice_profile.base_voice_id if voice_profile.base_voice_id else voice_id
        
        # For preset voices, merge preset parameters with user parameters
        # Preset parameters act as defaults that can be further adjusted
        if voice_profile.base_voice_id:
            # Apply preset parameters if they exist
            final_pitch = pitch * (voice_profile.pitch if voice_profile.pitch else 1.0)
            final_rate = rate * (voice_profile.rate if voice_profile.rate else 1.0)
            final_volume = volume * (voice_profile.volume if voice_profile.volume else 1.0)
        else:
            final_pitch = pitch
            final_rate = rate
            final_volume = volume
        
        # Build SSML with rate and pitch if not default
        rate_str = f"{int((final_rate - 1.0) * 100):+d}%" if final_rate != 1.0 else "+0%"
        pitch_str = f"{int((final_pitch - 1.0) * 50):+d}Hz" if final_pitch != 1.0 else "+0Hz"
        volume_str = f"{int((final_volume - 1.0) * 100):+d}%" if final_volume != 1.0 else "+0%"
        
        communicate = edge_tts.Communicate(
            text=text,
            voice=actual_voice_id,
            rate=rate_str,
            pitch=pitch_str,
            volume=volume_str
        )
        
        # Save to file
        output_filename = f"tts_{generation.id}_{int(time.time())}.mp3"
        output_path = AUDIO_DIR / output_filename
        
        await communicate.save(str(output_path))
        
        # Get file info
        file_size = output_path.stat().st_size
        
        # For duration, use a rough estimate (actual would need audio analysis)
        # Approximate: ~150 words per minute, ~5 chars per word
        estimated_duration = (len(text) / 5 / 150) * 60
        
        # Update generation record
        generation.file_path = str(output_path)
        generation.file_size_bytes = file_size
        generation.duration_seconds = estimated_duration
        generation.status = "completed"
        generation.completed_at = datetime.utcnow()
        db.commit()
        
        # Track usage event
        duration_ms = int((time.time() - start_time) * 1000)
        
        track_usage_event(
            db=db,
            visitor_id=visitor_id if not current_user else None,
            user_id=current_user.id if current_user else None,
            ip=ip,
            studio="audio",
            action="generate",
            tool="text_to_speech",
            success=True,
            duration_ms=duration_ms
        )
        
        # Log detailed audio event
        log_audio_event(
            db=db,
            request=request,
            action="generate",
            user_id=current_user.id if current_user else None,
            visitor_id=visitor_id if not current_user else None,
            voice_id=voice_id,
            voice_name=voice_profile.name,
            language=voice_profile.language,
            text_length=len(text),
            input_text=text,
            audio_duration=estimated_duration,
            file_size=file_size,
            processing_time_ms=duration_ms,
            status="success",
            generation_id=generation.id
        )
        
        return {
            "id": generation.id,
            "status": "completed",
            "file_url": f"/api/v1/audio/download/{generation.id}",
            "file_size": file_size,
            "duration": estimated_duration,
            "message": "Audio generated successfully"
        }
        
    except Exception as e:
        generation.status = "failed"
        generation.error_message = str(e)
        db.commit()
        
        # Track failed event
        duration_ms = int((time.time() - start_time) * 1000)
        
        track_usage_event(
            db=db,
            visitor_id=visitor_id if not current_user else None,
            user_id=current_user.id if current_user else None,
            ip=ip,
            studio="audio",
            action="generate",
            tool="text_to_speech",
            success=False,
            duration_ms=duration_ms
        )
        
        # Log detailed audio event
        log_audio_event(
            db=db,
            request=request,
            action="generate",
            user_id=current_user.id if current_user else None,
            visitor_id=visitor_id if not current_user else None,
            voice_id=voice_id,
            voice_name=voice_profile.name if voice_profile else None,
            language=voice_profile.language if voice_profile else None,
            text_length=len(text),
            input_text=text,
            processing_time_ms=duration_ms,
            status="failed",
            error_message=str(e),
            generation_id=generation.id
        )
        
        raise HTTPException(status_code=500, detail=f"TTS generation failed: {str(e)}")


@router.get("/download/{generation_id}")
def download_audio(
    request: Request,
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Download generated audio file. Works for guests and authenticated users."""
    import time
    start_time = time.time()
    
    visitor_id = request.headers.get("X-Visitor-Id")
    
    # Build query based on authentication
    query = db.query(TTSGeneration).filter(TTSGeneration.id == generation_id)
    
    if current_user:
        query = query.filter(TTSGeneration.user_id == current_user.id)
    else:
        if not visitor_id:
            raise HTTPException(status_code=400, detail="Visitor ID required for guest access")
        query = query.filter(TTSGeneration.visitor_id == visitor_id)
    
    generation = query.first()
    
    if not generation or not generation.file_path:
        # Return 404 for cross-visitor access attempts (security through obscurity)
        raise HTTPException(status_code=404, detail="Audio not found")
    
    file_path = Path(generation.file_path)
    if not file_path.exists():
        log_audio_event(
            db=db,
            request=request,
            action="download",
            user_id=current_user.id if current_user else None,
            visitor_id=visitor_id if not current_user else None,
            generation_id=generation_id,
            status="failed",
            error_message="File not found on disk",
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        raise HTTPException(status_code=404, detail="Audio file not found on disk")
    
    # Log successful download
    log_audio_event(
        db=db,
        request=request,
        action="download",
        user_id=current_user.id if current_user else None,
        visitor_id=visitor_id if not current_user else None,
        voice_id=generation.voice_id,
        voice_name=generation.voice_name,
        file_size=generation.file_size_bytes,
        audio_duration=generation.duration_seconds,
        generation_id=generation.id,
        status="success",
        processing_time_ms=int((time.time() - start_time) * 1000)
    )
    
    return FileResponse(
        path=str(file_path),
        media_type="audio/mpeg" if generation.output_format == "mp3" else "audio/wav",
        filename=f"tts_{generation.id}.{generation.output_format}"
    )


@router.get("/history/tts")
def get_tts_history(
    request: Request,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get TTS generation history. Works for guests and authenticated users."""
    visitor_id = request.headers.get("X-Visitor-Id")
    
    # Build query based on authentication
    if current_user:
        query = db.query(TTSGeneration).filter(TTSGeneration.user_id == current_user.id)
    else:
        if not visitor_id:
            raise HTTPException(status_code=400, detail="Visitor ID required for guest access")
        query = db.query(TTSGeneration).filter(TTSGeneration.visitor_id == visitor_id)
    
    total = query.count()
    generations = query.order_by(desc(TTSGeneration.created_at)).offset(offset).limit(limit).all()
    
    # Log the access
    log_audio_event(
        db=db,
        request=request,
        action="list_history_tts",
        user_id=current_user.id if current_user else None,
        visitor_id=visitor_id if not current_user else None,
        status="success"
    )
    
    return {
        "total": total,
        "items": [
            {
                "id": g.id,
                "text": g.input_text[:100] + "..." if len(g.input_text) > 100 else g.input_text,
                "full_text": g.input_text,
                "voice_name": g.voice_name,
                "duration": g.duration_seconds,
                "file_size": g.file_size_bytes,
                "status": g.status,
                "created_at": g.created_at.isoformat() if g.created_at else None,
                "download_url": f"/api/v1/audio/download/{g.id}" if g.status == "completed" else None
            }
            for g in generations
        ]
    }


@router.delete("/history/tts/{generation_id}")
def delete_tts_generation(
    request: Request,
    generation_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Delete a TTS generation. Works for guests and authenticated users."""
    visitor_id = request.headers.get("X-Visitor-Id")
    
    # Build query based on authentication
    query = db.query(TTSGeneration).filter(TTSGeneration.id == generation_id)
    
    if current_user:
        query = query.filter(TTSGeneration.user_id == current_user.id)
    else:
        if not visitor_id:
            raise HTTPException(status_code=400, detail="Visitor ID required for guest access")
        query = query.filter(TTSGeneration.visitor_id == visitor_id)
    
    generation = query.first()
    
    if not generation:
        # Return 404 for cross-visitor access attempts
        raise HTTPException(status_code=404, detail="Generation not found")
    
    # Delete file if exists
    if generation.file_path:
        file_path = Path(generation.file_path)
        if file_path.exists():
            file_path.unlink()
    
    # Log the deletion
    log_audio_event(
        db=db,
        request=request,
        action="delete_tts",
        user_id=current_user.id if current_user else None,
        visitor_id=visitor_id if not current_user else None,
        generation_id=generation_id,
        status="success"
    )
    
    db.delete(generation)
    db.commit()
    
    return {"message": "Generation deleted successfully"}


@router.post("/transcribe")
async def transcribe_audio(
    request: Request,
    audio: UploadFile = File(...),
    language: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Transcribe uploaded audio file using faster-whisper. Works for guests and authenticated users."""
    import time
    start_time = time.time()
    
    visitor_id = request.headers.get("X-Visitor-Id")
    forwarded_for = request.headers.get("X-Forwarded-For")
    ip = get_client_ip(request, forwarded_for)
    
    # For guests, check rate limits and file size
    if not current_user:
        if not visitor_id:
            log_audio_event(
                db=db,
                request=request,
                action="transcribe",
                status="failed",
                error_message="Missing X-Visitor-Id header",
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            raise HTTPException(status_code=400, detail="Visitor ID required for guest access")
        
        if check_rate_limit(db, visitor_id, ip, limit_per_hour=50):
            log_audio_event(
                db=db,
                request=request,
                action="transcribe",
                visitor_id=visitor_id,
                status="rate_limited",
                error_message="Rate limit exceeded (50 per hour for guests)",
                processing_time_ms=int((time.time() - start_time) * 1000)
            )
            raise HTTPException(
                status_code=429, 
                detail="Rate limit exceeded. Please sign in for unlimited access or try again later."
            )
    
    # Check file size (stricter for guests: 10MB vs 50MB)
    max_size = 50 * 1024 * 1024 if current_user else 10 * 1024 * 1024
    content = await audio.read()
    if len(content) > max_size:
        log_audio_event(
            db=db,
            request=request,
            action="transcribe",
            user_id=current_user.id if current_user else None,
            visitor_id=visitor_id if not current_user else None,
            file_size=len(content),
            status="failed",
            error_message=f"File too large (max {max_size // 1024 // 1024}MB)",
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        raise HTTPException(
            status_code=400,
            detail=f"File too large (max {max_size // 1024 // 1024}MB for {'users' if current_user else 'guests'})"
        )
    
    # Create transcription record
    transcription = Transcription(
        user_id=current_user.id if current_user else None,
        visitor_id=visitor_id if not current_user else None,
        source_type="upload",
        language=language,
        status="processing"
    )
    db.add(transcription)
    db.commit()
    db.refresh(transcription)
    
    try:
        # Check if faster-whisper is available
        try:
            from faster_whisper import WhisperModel
        except ImportError:
            transcription.status = "failed"
            transcription.error_message = "Whisper not installed. Run: pip install faster-whisper"
            db.commit()
            raise HTTPException(
                status_code=503,
                detail="Whisper transcription not available. Install faster-whisper package."
            )
        
        # Check if ffmpeg is available
        import shutil
        if not shutil.which("ffmpeg"):
            transcription.status = "failed"
            transcription.error_message = "FFmpeg not found. Please install FFmpeg: https://ffmpeg.org/download.html"
            db.commit()
            raise HTTPException(
                status_code=503,
                detail="FFmpeg is required for audio transcription but was not found. Please install FFmpeg."
            )
        
        # Save uploaded file temporarily
        original_ext = audio.filename.split('.')[-1] if '.' in audio.filename else 'mp3'
        upload_filename = f"upload_{transcription.id}_{int(time.time())}.{original_ext}"
        upload_path = AUDIO_DIR / upload_filename
        
        # Content already read for size check
        with open(upload_path, "wb") as f:
            f.write(content)
        
        # Convert to WAV format for compatibility (fixes metadata_errors issue)
        # This ensures consistent format regardless of upload type (mp3/webm/wav/etc)
        import subprocess
        wav_filename = f"upload_{transcription.id}_{int(time.time())}_converted.wav"
        wav_path = AUDIO_DIR / wav_filename
        
        try:
            subprocess.run(
                ["ffmpeg", "-i", str(upload_path), "-ar", "16000", "-ac", "1", "-y", str(wav_path)],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            transcription.status = "failed"
            transcription.error_message = f"Audio conversion failed: {e.stderr.decode()}"
            db.commit()
            raise HTTPException(status_code=400, detail="Failed to process audio file. Please check the format.")
        
        transcription.source_file = str(wav_path)
        db.commit()
        
        # Load Whisper model (tiny for speed on CPU)
        # Model is downloaded to ~/.cache/huggingface/hub/ on first use (~75MB for tiny model)
        model_size = os.getenv("WHISPER_MODEL_SIZE", "tiny")
        model = WhisperModel(model_size, device="cpu", compute_type="int8")
        
        # Decode audio ourselves to bypass faster-whisper's av decoder
        # This avoids the metadata_errors parameter incompatibility
        import wave
        import numpy as np
        
        with wave.open(str(wav_path), 'rb') as wav_file:
            # Read audio data
            audio_data = wav_file.readframes(wav_file.getnframes())
            # Convert to numpy array (int16)
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            # Convert to float32 in range [-1, 1]
            audio_float = audio_np.astype(np.float32) / 32768.0
        
        # Transcribe the numpy array directly
        segments_list, info = model.transcribe(
            audio_float,
            language=language if language else None,
            beam_size=5
        )
        
        # Clean up original upload file
        if upload_path.exists() and upload_path != wav_path:
            upload_path.unlink()
        
        # Collect segments with timestamps
        segments_data = []
        full_text_parts = []
        
        for segment in segments_list:
            segments_data.append({
                "start": segment.start,
                "end": segment.end,
                "text": segment.text.strip()
            })
            full_text_parts.append(segment.text.strip())
        
        full_text = " ".join(full_text_parts)
        
        # Generate SRT file
        srt_filename = f"transcript_{transcription.id}.srt"
        srt_path = AUDIO_DIR / srt_filename
        
        with open(srt_path, "w", encoding="utf-8") as f:
            for i, seg in enumerate(segments_data, 1):
                f.write(f"{i}\n")
                f.write(f"{format_timestamp(seg['start'])} --> {format_timestamp(seg['end'])}\n")
                f.write(f"{seg['text']}\n\n")
        
        # Generate TXT file
        txt_filename = f"transcript_{transcription.id}.txt"
        txt_path = AUDIO_DIR / txt_filename
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_text)
        
        # Update transcription record
        transcription.transcript_text = full_text
        transcription.segments_json = json.dumps(segments_data)
        transcription.language_detected = info.language if hasattr(info, "language") else language
        transcription.duration_seconds = info.duration if hasattr(info, "duration") else None
        transcription.txt_file = str(txt_path)
        transcription.srt_file = str(srt_path)
        transcription.status = "completed"
        transcription.completed_at = datetime.utcnow()
        db.commit()
        
        # Track usage event
        duration_ms = int((time.time() - start_time) * 1000)
        
        track_usage_event(
            db=db,
            visitor_id=visitor_id if not current_user else None,
            user_id=current_user.id if current_user else None,
            ip=ip,
            studio="audio",
            action="transcribe",
            tool="speech_to_text",
            success=True,
            duration_ms=duration_ms
        )
        
        # Log detailed audio event
        log_audio_event(
            db=db,
            request=request,
            action="transcribe",
            user_id=current_user.id if current_user else None,
            visitor_id=visitor_id if not current_user else None,
            language=transcription.language_detected,
            text_length=len(full_text) if full_text else None,
            audio_duration=transcription.duration_seconds,
            file_size=len(content),
            processing_time_ms=duration_ms,
            status="success",
            transcription_id=transcription.id
        )
        
        return {
            "id": transcription.id,
            "status": "completed",
            "text": full_text,
            "language": transcription.language_detected,
            "duration": transcription.duration_seconds,
            "segments": segments_data,
            "txt_url": f"/api/v1/audio/download/transcript/{transcription.id}/txt",
            "srt_url": f"/api/v1/audio/download/transcript/{transcription.id}/srt",
            "message": "Transcription completed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        transcription.status = "failed"
        transcription.error_message = str(e)
        db.commit()
        
        # Track failed event
        duration_ms = int((time.time() - start_time) * 1000)
        
        track_usage_event(
            db=db,
            visitor_id=visitor_id if not current_user else None,
            user_id=current_user.id if current_user else None,
            ip=ip,
            studio="audio",
            action="transcribe",
            tool="speech_to_text",
            success=False,
            duration_ms=duration_ms
        )
        
        # Log detailed audio event
        log_audio_event(
            db=db,
            request=request,
            action="transcribe",
            user_id=current_user.id if current_user else None,
            visitor_id=visitor_id if not current_user else None,
            language=language,
            file_size=len(content) if 'content' in locals() else None,
            processing_time_ms=duration_ms,
            status="failed",
            error_message=str(e),
            transcription_id=transcription.id
        )
        
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")


def format_timestamp(seconds: float) -> str:
    """Format seconds to SRT timestamp format: HH:MM:SS,mmm"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


@router.get("/download/transcript/{transcription_id}/{format}")
def download_transcript(
    request: Request,
    transcription_id: int,
    format: str,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Download transcript in txt or srt format. Works for guests and authenticated users."""
    import time
    start_time = time.time()
    
    visitor_id = request.headers.get("X-Visitor-Id")
    
    # Build query based on authentication
    query = db.query(Transcription).filter(Transcription.id == transcription_id)
    
    if current_user:
        query = query.filter(Transcription.user_id == current_user.id)
    else:
        if not visitor_id:
            raise HTTPException(status_code=400, detail="Visitor ID required for guest access")
        query = query.filter(Transcription.visitor_id == visitor_id)
    
    transcription = query.first()
    
    if not transcription:
        # Return 404 for cross-visitor access attempts
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    if format == "txt":
        file_path = transcription.txt_file
        media_type = "text/plain"
        filename = f"transcript_{transcription_id}.txt"
    elif format == "srt":
        file_path = transcription.srt_file
        media_type = "text/plain"
        filename = f"transcript_{transcription_id}.srt"
    else:
        raise HTTPException(status_code=400, detail="Format must be txt or srt")
    
    if not file_path or not Path(file_path).exists():
        log_audio_event(
            db=db,
            request=request,
            action=f"download_transcript_{format}",
            user_id=current_user.id if current_user else None,
            visitor_id=visitor_id if not current_user else None,
            transcription_id=transcription_id,
            status="failed",
            error_message="File not found",
            processing_time_ms=int((time.time() - start_time) * 1000)
        )
        raise HTTPException(status_code=404, detail="Transcript file not found")
    
    # Log successful download
    log_audio_event(
        db=db,
        request=request,
        action=f"download_transcript_{format}",
        user_id=current_user.id if current_user else None,
        visitor_id=visitor_id if not current_user else None,
        transcription_id=transcription_id,
        language=transcription.language_detected,
        status="success",
        processing_time_ms=int((time.time() - start_time) * 1000)
    )
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=filename
    )


@router.get("/history/transcriptions")
def get_transcription_history(
    request: Request,
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Get transcription history. Works for guests and authenticated users."""
    visitor_id = request.headers.get("X-Visitor-Id")
    
    # Build query based on authentication
    if current_user:
        query = db.query(Transcription).filter(Transcription.user_id == current_user.id)
    else:
        if not visitor_id:
            raise HTTPException(status_code=400, detail="Visitor ID required for guest access")
        query = db.query(Transcription).filter(Transcription.visitor_id == visitor_id)
    
    total = query.count()
    transcriptions = query.order_by(desc(Transcription.created_at)).offset(offset).limit(limit).all()
    
    # Log the access
    log_audio_event(
        db=db,
        request=request,
        action="list_history_transcriptions",
        user_id=current_user.id if current_user else None,
        visitor_id=visitor_id if not current_user else None,
        status="success"
    )
    
    return {
        "total": total,
        "items": [
            {
                "id": t.id,
                "text": t.transcript_text[:100] + "..." if t.transcript_text and len(t.transcript_text) > 100 else t.transcript_text,
                "full_text": t.transcript_text,
                "language": t.language_detected or t.language,
                "duration": t.duration_seconds,
                "status": t.status,
                "created_at": t.created_at.isoformat() if t.created_at else None,
                "txt_url": f"/api/v1/audio/download/transcript/{t.id}/txt" if t.status == "completed" else None,
                "srt_url": f"/api/v1/audio/download/transcript/{t.id}/srt" if t.status == "completed" else None
            }
            for t in transcriptions
        ]
    }


@router.delete("/history/transcriptions/{transcription_id}")
def delete_transcription(
    request: Request,
    transcription_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """Delete a transcription. Works for guests and authenticated users."""
    visitor_id = request.headers.get("X-Visitor-Id")
    
    # Build query based on authentication
    query = db.query(Transcription).filter(Transcription.id == transcription_id)
    
    if current_user:
        query = query.filter(Transcription.user_id == current_user.id)
    else:
        if not visitor_id:
            raise HTTPException(status_code=400, detail="Visitor ID required for guest access")
        query = query.filter(Transcription.visitor_id == visitor_id)
    
    transcription = query.first()
    
    if not transcription:
        # Return 404 for cross-visitor access attempts
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    # Delete files if exist
    for file_path in [transcription.source_file, transcription.txt_file, transcription.srt_file]:
        if file_path:
            path = Path(file_path)
            if path.exists():
                path.unlink()
    
    # Log the deletion
    log_audio_event(
        db=db,
        request=request,
        action="delete_transcription",
        user_id=current_user.id if current_user else None,
        visitor_id=visitor_id if not current_user else None,
        transcription_id=transcription_id,
        status="success"
    )
    
    db.delete(transcription)
    db.commit()
    
    return {"message": "Transcription deleted successfully"}


@router.post("/events")
def log_client_event(
    request: Request,
    action: str = Form(...),
    generation_id: Optional[int] = Form(None),
    transcription_id: Optional[int] = Form(None),
    voice_id: Optional[str] = Form(None),
    voice_name: Optional[str] = Form(None),
    language: Optional[str] = Form(None),
    audio_duration: Optional[float] = Form(None),
    file_size: Optional[int] = Form(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user)
):
    """
    Log client-side audio events (play, download, etc.).
    Works for guests and authenticated users.
    """
    import time
    start_time = time.time()
    
    visitor_id = request.headers.get("X-Visitor-Id")
    
    # For guests, require visitor ID
    if not current_user and not visitor_id:
        raise HTTPException(status_code=400, detail="Visitor ID required for guest access")
    
    # Log the event
    log_audio_event(
        db=db,
        request=request,
        action=action,
        user_id=current_user.id if current_user else None,
        visitor_id=visitor_id if not current_user else None,
        voice_id=voice_id,
        voice_name=voice_name,
        language=language,
        audio_duration=audio_duration,
        file_size=file_size,
        generation_id=generation_id,
        transcription_id=transcription_id,
        status="success",
        processing_time_ms=int((time.time() - start_time) * 1000)
    )
    
    return {"status": "logged"}
