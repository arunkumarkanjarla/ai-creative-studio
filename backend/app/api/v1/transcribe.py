from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
import tempfile
import os
import time

from app.db.database import get_db
from app.core.analytics import track_usage_event, get_client_ip
from app.api.v1.dependencies import get_optional_user

router = APIRouter()

@router.post("/transcribe")
async def transcribe_audio(
    request: Request,
    audio: UploadFile = File(...),
    language: str = Form("en"),
    db: Session = Depends(get_db),
    current_user = Depends(get_optional_user),
):
    """
    Transcribe audio using Whisper (local faster-whisper).
    Falls back to basic response if Whisper not available.
    """
    start_time = time.time()
    visitor_id = request.headers.get("X-Visitor-Id")
    forwarded_for = request.headers.get("X-Forwarded-For")
    ip = get_client_ip(request, forwarded_for)
    success = False
    
    try:
        # Check if faster-whisper is available
        try:
            from faster_whisper import WhisperModel
            
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_file:
                content = await audio.read()
                tmp_file.write(content)
                tmp_file_path = tmp_file.name
            
            try:
                # Load Whisper model (tiny for speed, can be configured)
                model_size = os.getenv("WHISPER_MODEL_SIZE", "tiny")
                model = WhisperModel(model_size, device="cpu", compute_type="int8")
                
                # Transcribe
                segments, info = model.transcribe(
                    tmp_file_path,
                    language=language if language != "en" else None,
                    beam_size=5
                )
                
                # Combine all segments
                transcription = " ".join([segment.text for segment in segments])
                
                success = True
                duration_ms = int((time.time() - start_time) * 1000)
                
                # Track successful transcription
                track_usage_event(
                    db=db,
                    visitor_id=visitor_id,
                    user_id=current_user.id if current_user else None,
                    ip=ip,
                    studio=None,
                    action="voice_input",
                    tool="whisper",
                    success=True,
                    duration_ms=duration_ms,
                )
                
                return JSONResponse({
                    "text": transcription.strip(),
                    "language": info.language if hasattr(info, "language") else language,
                    "method": "whisper"
                })
                
            finally:
                # Clean up temp file
                if os.path.exists(tmp_file_path):
                    os.remove(tmp_file_path)
                    
        except ImportError:
            # Whisper not installed - return helpful message
            duration_ms = int((time.time() - start_time) * 1000)
            track_usage_event(
                db=db,
                visitor_id=visitor_id,
                user_id=current_user.id if current_user else None,
                ip=ip,
                studio=None,
                action="voice_input",
                tool="whisper",
                success=False,
                duration_ms=duration_ms,
            )
            return JSONResponse({
                "text": "",
                "error": "Whisper transcription not available. Install faster-whisper: pip install faster-whisper",
                "method": "none"
            }, status_code=503)
            
    except Exception as e:
        # Track failed transcription
        if not success:
            duration_ms = int((time.time() - start_time) * 1000)
            track_usage_event(
                db=db,
                visitor_id=visitor_id,
                user_id=current_user.id if current_user else None,
                ip=ip,
                studio=None,
                action="voice_input",
                tool="whisper",
                success=False,
                duration_ms=duration_ms,
            )
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
