from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import func, or_, desc, asc
from sqlalchemy.orm import Session
from pathlib import Path
import csv
import io

from app.api.v1.dependencies import require_admin
from app.db.database import get_db
from app.models.user import User
from app.models.audio import VoiceProfile, TTSGeneration, Transcription

router = APIRouter(prefix="/admin/audio", tags=["Admin Audio"])

# Audio storage directory
BACKEND_DIR = Path(__file__).resolve().parents[3]
AUDIO_DIR = BACKEND_DIR / "generated_audio"


@router.get("/generated/summary")
def get_generated_audio_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Get summary statistics for all generated TTS audio."""
    # Total counts
    total_files = db.query(func.count(TTSGeneration.id)).scalar()
    total_size = db.query(func.sum(TTSGeneration.file_size)).scalar() or 0
    total_duration = db.query(func.sum(TTSGeneration.duration)).scalar() or 0.0
    
    # Today's count
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = db.query(func.count(TTSGeneration.id)).filter(
        TTSGeneration.created_at >= today_start
    ).scalar()
    
    return {
        "total_files": total_files,
        "total_size": total_size,
        "total_duration": round(total_duration, 2),
        "today_count": today_count
    }


@router.get("/generated/list")
def list_generated_audio(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    user_type: Optional[str] = None,  # "user", "guest", or None for all
    voice: Optional[str] = None,
    language: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: str = Query("created_at", regex="^(created_at|duration|file_size)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$")
):
    """List all generated TTS audio with filters and pagination."""
    query = db.query(TTSGeneration)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                TTSGeneration.text.ilike(f"%{search}%"),
                TTSGeneration.full_text.ilike(f"%{search}%")
            )
        )
    
    if user_type == "user":
        query = query.filter(TTSGeneration.user_id.isnot(None))
    elif user_type == "guest":
        query = query.filter(TTSGeneration.user_id.is_(None))
    
    if voice:
        query = query.filter(TTSGeneration.voice_name == voice)
    
    if language:
        query = query.filter(TTSGeneration.language == language)
    
    if status:
        query = query.filter(TTSGeneration.status == status)
    
    if date_from:
        try:
            from_date = datetime.fromisoformat(date_from)
            query = query.filter(TTSGeneration.created_at >= from_date)
        except ValueError:
            pass
    
    if date_to:
        try:
            to_date = datetime.fromisoformat(date_to)
            query = query.filter(TTSGeneration.created_at <= to_date)
        except ValueError:
            pass
    
    # Total count before pagination
    total = query.count()
    
    # Sorting
    sort_col = getattr(TTSGeneration, sort_by)
    if sort_order == "desc":
        query = query.order_by(desc(sort_col))
    else:
        query = query.order_by(asc(sort_col))
    
    # Pagination
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()
    
    # Build response with user info
    results = []
    for item in items:
        user_info = None
        if item.user_id:
            user = db.query(User).filter(User.id == item.user_id).first()
            if user:
                user_info = {
                    "type": "user",
                    "name": user.name,
                    "email": user.email
                }
        else:
            user_info = {
                "type": "guest",
                "visitor_id": item.visitor_id[:8] if item.visitor_id else "unknown",
                "ip": item.ip_address
            }
        
        # Get voice info
        voice_info = {}
        if item.voice_id:
            voice = db.query(VoiceProfile).filter(VoiceProfile.voice_id == item.voice_id).first()
            if voice:
                voice_info = {
                    "name": voice.name,
                    "language": voice.language,
                    "region": voice.region,
                    "gender": voice.gender,
                    "voice_type": voice.voice_type
                }
        
        # Check if file exists
        file_exists = False
        if item.file_path:
            file_path = AUDIO_DIR / item.file_path.lstrip('/')
            file_exists = file_path.exists()
        
        results.append({
            "id": item.id,
            "user": user_info,
            "voice": voice_info,
            "text_preview": item.text,
            "full_text": item.full_text,
            "pitch": item.pitch,
            "rate": item.rate,
            "volume": item.volume,
            "output_format": item.output_format,
            "duration": item.duration,
            "file_size": item.file_size,
            "status": item.status,
            "created_at": item.created_at.isoformat(),
            "file_path": item.file_path,
            "file_exists": file_exists,
            "download_url": item.download_url if file_exists else None
        })
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "items": results
    }


@router.get("/generated/{generation_id}/download")
def download_generated_audio(
    generation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Download a generated audio file."""
    generation = db.query(TTSGeneration).filter(TTSGeneration.id == generation_id).first()
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    if not generation.file_path:
        raise HTTPException(status_code=404, detail="No file path")
    
    file_path = AUDIO_DIR / generation.file_path.lstrip('/')
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")
    
    return FileResponse(
        path=str(file_path),
        media_type=f"audio/{generation.output_format}",
        filename=f"tts_{generation.id}.{generation.output_format}"
    )


@router.delete("/generated/{generation_id}")
def delete_generated_audio(
    generation_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Delete a generated audio file."""
    generation = db.query(TTSGeneration).filter(TTSGeneration.id == generation_id).first()
    if not generation:
        raise HTTPException(status_code=404, detail="Generation not found")
    
    # Delete file from disk if it exists
    if generation.file_path:
        file_path = AUDIO_DIR / generation.file_path.lstrip('/')
        if file_path.exists():
            file_path.unlink()
    
    # Delete from database
    db.delete(generation)
    db.commit()
    
    return {"message": "Deleted successfully"}


@router.post("/generated/bulk-delete")
def bulk_delete_generated_audio(
    generation_ids: list[int],
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Bulk delete generated audio files."""
    deleted = 0
    for gen_id in generation_ids:
        generation = db.query(TTSGeneration).filter(TTSGeneration.id == gen_id).first()
        if generation:
            # Delete file from disk
            if generation.file_path:
                file_path = AUDIO_DIR / generation.file_path.lstrip('/')
                if file_path.exists():
                    file_path.unlink()
            
            db.delete(generation)
            deleted += 1
    
    db.commit()
    return {"deleted": deleted}


@router.get("/generated/export")
def export_generated_audio_csv(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    search: Optional[str] = None,
    user_type: Optional[str] = None,
    voice: Optional[str] = None,
    language: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Export generated audio list to CSV."""
    query = db.query(TTSGeneration)
    
    # Apply same filters as list endpoint
    if search:
        query = query.filter(
            or_(
                TTSGeneration.text.ilike(f"%{search}%"),
                TTSGeneration.full_text.ilike(f"%{search}%")
            )
        )
    
    if user_type == "user":
        query = query.filter(TTSGeneration.user_id.isnot(None))
    elif user_type == "guest":
        query = query.filter(TTSGeneration.user_id.is_(None))
    
    if voice:
        query = query.filter(TTSGeneration.voice_name == voice)
    
    if language:
        query = query.filter(TTSGeneration.language == language)
    
    if status:
        query = query.filter(TTSGeneration.status == status)
    
    if date_from:
        try:
            query = query.filter(TTSGeneration.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    
    if date_to:
        try:
            query = query.filter(TTSGeneration.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass
    
    items = query.order_by(desc(TTSGeneration.created_at)).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "User Type", "User Name/Email", "Visitor ID", "IP",
        "Voice", "Language", "Region", "Text Preview", "Duration",
        "File Size", "Status", "Created At"
    ])
    
    for item in items:
        user_type = "user" if item.user_id else "guest"
        user_name = ""
        visitor_id = ""
        ip = item.ip_address or ""
        
        if item.user_id:
            user = db.query(User).filter(User.id == item.user_id).first()
            user_name = user.name if user else ""
        else:
            visitor_id = item.visitor_id[:8] if item.visitor_id else ""
        
        voice_name = ""
        language = ""
        region = ""
        if item.voice_id:
            voice = db.query(VoiceProfile).filter(VoiceProfile.voice_id == item.voice_id).first()
            if voice:
                voice_name = voice.name
                language = voice.language
                region = voice.region or ""
        
        writer.writerow([
            item.id,
            user_type,
            user_name,
            visitor_id,
            ip,
            voice_name,
            language,
            region,
            item.text[:100],
            item.duration,
            item.file_size,
            item.status,
            item.created_at.isoformat()
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=generated_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )


# Transcriptions endpoints

@router.get("/transcriptions/summary")
def get_transcriptions_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Get summary statistics for all transcriptions."""
    total_files = db.query(func.count(Transcription.id)).scalar()
    total_duration = db.query(func.sum(Transcription.duration)).scalar() or 0.0
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = db.query(func.count(Transcription.id)).filter(
        Transcription.created_at >= today_start
    ).scalar()
    
    return {
        "total_files": total_files,
        "total_duration": round(total_duration, 2),
        "today_count": today_count
    }


@router.get("/transcriptions/list")
def list_transcriptions(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    user_type: Optional[str] = None,
    language: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: str = Query("created_at", regex="^(created_at|duration)$"),
    sort_order: str = Query("desc", regex="^(asc|desc)$")
):
    """List all transcriptions with filters and pagination."""
    query = db.query(Transcription)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Transcription.text.ilike(f"%{search}%"),
                Transcription.full_text.ilike(f"%{search}%")
            )
        )
    
    if user_type == "user":
        query = query.filter(Transcription.user_id.isnot(None))
    elif user_type == "guest":
        query = query.filter(Transcription.user_id.is_(None))
    
    if language:
        query = query.filter(Transcription.language == language)
    
    if status:
        query = query.filter(Transcription.status == status)
    
    if date_from:
        try:
            query = query.filter(Transcription.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    
    if date_to:
        try:
            query = query.filter(Transcription.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass
    
    # Total count
    total = query.count()
    
    # Sorting
    sort_col = getattr(Transcription, sort_by)
    if sort_order == "desc":
        query = query.order_by(desc(sort_col))
    else:
        query = query.order_by(asc(sort_col))
    
    # Pagination
    offset = (page - 1) * limit
    items = query.offset(offset).limit(limit).all()
    
    # Build response
    results = []
    for item in items:
        user_info = None
        if item.user_id:
            user = db.query(User).filter(User.id == item.user_id).first()
            if user:
                user_info = {
                    "type": "user",
                    "name": user.name,
                    "email": user.email
                }
        else:
            user_info = {
                "type": "guest",
                "visitor_id": item.visitor_id[:8] if item.visitor_id else "unknown",
                "ip": item.ip_address
            }
        
        # Check if files exist
        txt_exists = False
        srt_exists = False
        if item.txt_path:
            txt_path = AUDIO_DIR / item.txt_path.lstrip('/')
            txt_exists = txt_path.exists()
        if item.srt_path:
            srt_path = AUDIO_DIR / item.srt_path.lstrip('/')
            srt_exists = srt_path.exists()
        
        results.append({
            "id": item.id,
            "user": user_info,
            "text_preview": item.text,
            "full_text": item.full_text,
            "language": item.language,
            "duration": item.duration,
            "status": item.status,
            "created_at": item.created_at.isoformat(),
            "txt_url": item.txt_url if txt_exists else None,
            "srt_url": item.srt_url if srt_exists else None,
            "txt_exists": txt_exists,
            "srt_exists": srt_exists
        })
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
        "items": results
    }


@router.delete("/transcriptions/{transcription_id}")
def delete_transcription(
    transcription_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Delete a transcription."""
    transcription = db.query(Transcription).filter(Transcription.id == transcription_id).first()
    if not transcription:
        raise HTTPException(status_code=404, detail="Transcription not found")
    
    # Delete files from disk
    if transcription.txt_path:
        txt_path = AUDIO_DIR / transcription.txt_path.lstrip('/')
        if txt_path.exists():
            txt_path.unlink()
    
    if transcription.srt_path:
        srt_path = AUDIO_DIR / transcription.srt_path.lstrip('/')
        if srt_path.exists():
            srt_path.unlink()
    
    db.delete(transcription)
    db.commit()
    
    return {"message": "Deleted successfully"}


@router.post("/transcriptions/bulk-delete")
def bulk_delete_transcriptions(
    transcription_ids: list[int],
    db: Session = Depends(get_db),
    _: User = Depends(require_admin)
):
    """Bulk delete transcriptions."""
    deleted = 0
    for trans_id in transcription_ids:
        transcription = db.query(Transcription).filter(Transcription.id == trans_id).first()
        if transcription:
            if transcription.txt_path:
                txt_path = AUDIO_DIR / transcription.txt_path.lstrip('/')
                if txt_path.exists():
                    txt_path.unlink()
            
            if transcription.srt_path:
                srt_path = AUDIO_DIR / transcription.srt_path.lstrip('/')
                if srt_path.exists():
                    srt_path.unlink()
            
            db.delete(transcription)
            deleted += 1
    
    db.commit()
    return {"deleted": deleted}


@router.get("/transcriptions/export")
def export_transcriptions_csv(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    search: Optional[str] = None,
    user_type: Optional[str] = None,
    language: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None
):
    """Export transcriptions to CSV."""
    query = db.query(Transcription)
    
    # Apply filters
    if search:
        query = query.filter(
            or_(
                Transcription.text.ilike(f"%{search}%"),
                Transcription.full_text.ilike(f"%{search}%")
            )
        )
    
    if user_type == "user":
        query = query.filter(Transcription.user_id.isnot(None))
    elif user_type == "guest":
        query = query.filter(Transcription.user_id.is_(None))
    
    if language:
        query = query.filter(Transcription.language == language)
    
    if status:
        query = query.filter(Transcription.status == status)
    
    if date_from:
        try:
            query = query.filter(Transcription.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    
    if date_to:
        try:
            query = query.filter(Transcription.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass
    
    items = query.order_by(desc(Transcription.created_at)).all()
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "User Type", "User Name/Email", "Visitor ID", "IP",
        "Language", "Text Preview", "Duration", "Status", "Created At"
    ])
    
    for item in items:
        user_type = "user" if item.user_id else "guest"
        user_name = ""
        visitor_id = ""
        ip = item.ip_address or ""
        
        if item.user_id:
            user = db.query(User).filter(User.id == item.user_id).first()
            user_name = user.name if user else ""
        else:
            visitor_id = item.visitor_id[:8] if item.visitor_id else ""
        
        writer.writerow([
            item.id,
            user_type,
            user_name,
            visitor_id,
            ip,
            item.language,
            item.text[:100],
            item.duration,
            item.status,
            item.created_at.isoformat()
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=transcriptions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )
