from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import tempfile
import os

router = APIRouter()

@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("en")
):
    """
    Transcribe audio using Whisper (local faster-whisper).
    Falls back to basic response if Whisper not available.
    """
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
            return JSONResponse({
                "text": "",
                "error": "Whisper transcription not available. Install faster-whisper: pip install faster-whisper",
                "method": "none"
            }, status_code=503)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
