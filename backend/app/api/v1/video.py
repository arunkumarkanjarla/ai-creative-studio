"""
Video Studio API — authenticated users only.
"""
from __future__ import annotations

import json
import mimetypes
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from fastapi.responses import FileResponse, Response, StreamingResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session, joinedload

from app.api.v1.dependencies import get_current_user, require_studio_access
from app.core.analytics import get_client_ip, track_usage_event
from app.core.video_events import check_video_rate_limit, log_video_event
from app.db.database import get_db
from app.models.user import User
from app.models.video import VideoCharacter, VideoProject, VideoScene
from app.services.video.categories import (
    CATEGORIES,
    GPU_ONLY_RESOLUTIONS,
    LENGTH_PRESETS,
    resolve_duration,
)
from app.services.video.engines import list_engines
from app.services.video.job_runner import enqueue_video_job

router = APIRouter(prefix="/video", tags=["Video Studio"])

BACKEND_DIR = Path(__file__).resolve().parents[3]
VIDEO_DIR = BACKEND_DIR / "generated_videos"
CHAR_DIR = VIDEO_DIR / "characters"
CHAR_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_CHARACTERS = 6
RATE_LIMIT_PER_HOUR = 20


def _project_to_dict(project: VideoProject, include_relations: bool = True) -> dict:
    data = {
        "id": project.id,
        "prompt": project.prompt,
        "category": project.category,
        "length_preset": project.length_preset,
        "duration_seconds": project.duration_seconds,
        "orientation": project.orientation,
        "resolution": project.resolution,
        "fps": project.fps,
        "audio_mode": project.audio_mode,
        "subtitles": project.subtitles,
        "output_format": project.output_format,
        "engine": project.engine,
        "status": project.status,
        "progress": project.progress,
        "error_message": project.error_message,
        "file_size_bytes": project.file_size_bytes,
        "generation_time_seconds": project.generation_time_seconds,
        "created_at": project.created_at.isoformat() if project.created_at else None,
        "completed_at": project.completed_at.isoformat() if project.completed_at else None,
        "has_output": bool(project.output_path and Path(project.output_path).exists()),
        "has_thumbnail": bool(project.thumbnail_path and Path(project.thumbnail_path).exists()),
        "stream_url": f"/api/v1/video/{project.id}/stream" if project.output_path else None,
        "download_url": f"/api/v1/video/{project.id}/download" if project.output_path else None,
        "thumbnail_url": f"/api/v1/video/{project.id}/thumbnail" if project.thumbnail_path else None,
    }
    if include_relations:
        data["scenes"] = [
            {
                "id": s.id,
                "scene_index": s.scene_index,
                "prompt": s.prompt,
                "dialogue_text": s.dialogue_text,
                "character_name": s.character_name,
                "duration_seconds": s.duration_seconds,
            }
            for s in (project.scenes or [])
        ]
        data["characters"] = [
            {
                "id": c.id,
                "character_index": c.character_index,
                "name": c.name,
                "voice_id": c.voice_id,
                "has_image": bool(c.image_path and Path(c.image_path).exists()),
            }
            for c in (project.characters or [])
        ]
    return data


def _resolve_path(stored: str | None) -> Path | None:
    if not stored:
        return None
    path = Path(stored)
    if path.is_absolute():
        return path
    return VIDEO_DIR / stored.lstrip("/")


@router.get("/meta")
def video_meta(
    current_user: User = Depends(require_studio_access("video")),
):
    """Category defaults, length presets, and engine availability."""
    return {
        "categories": [
            {"id": key, **{k: v for k, v in val.items()}}
            for key, val in CATEGORIES.items()
        ],
        "length_presets": LENGTH_PRESETS,
        "resolutions": [
            {"id": "480p", "gpu_only": False},
            {"id": "720p", "gpu_only": False},
            {"id": "1080p", "gpu_only": False},
            {"id": "1440p", "gpu_only": True},
            {"id": "4k", "gpu_only": True},
        ],
        "orientations": ["landscape", "portrait", "square"],
        "fps_options": [24, 25, 30],
        "audio_modes": [
            "dialogue",
            "voiceover",
            "background_music",
            "dialogue_music",
            "silent",
        ],
        "output_formats": ["mp4", "webm"],
        "engines": [c.__dict__ for c in list_engines()],
        "limits": {
            "max_characters": MAX_CHARACTERS,
            "max_image_bytes": MAX_IMAGE_BYTES,
            "rate_limit_per_hour": RATE_LIMIT_PER_HOUR,
        },
        "user_id": current_user.id,
    }


@router.post("/generate")
async def create_video(
    request: Request,
    prompt: str = Form(...),
    category: str = Form("custom"),
    length_preset: str = Form("short"),
    duration_seconds: Optional[float] = Form(None),
    orientation: str = Form("portrait"),
    resolution: str = Form("720p"),
    fps: int = Form(24),
    audio_mode: str = Form("dialogue"),
    subtitles: bool = Form(True),
    output_format: str = Form("mp4"),
    engine: str = Form("local"),
    scenes_json: str = Form("[]"),
    characters_json: str = Form("[]"),
    character_images: Optional[List[UploadFile]] = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_studio_access("video")),
):
    """Create a video generation job (multipart). Auth required."""
    start = time.time()

    if check_video_rate_limit(db, current_user.id, RATE_LIMIT_PER_HOUR):
        log_video_event(
            db,
            request,
            action="create",
            user_id=current_user.id,
            status="rate_limited",
            error_message="Rate limit exceeded",
        )
        raise HTTPException(status_code=429, detail="Video generation rate limit exceeded (20/hour)")

    if not prompt.strip():
        raise HTTPException(status_code=400, detail="Prompt is required")

    if category not in CATEGORIES:
        raise HTTPException(status_code=400, detail="Invalid category")

    if resolution in GPU_ONLY_RESOLUTIONS and engine == "local":
        raise HTTPException(
            status_code=400,
            detail=f"{resolution} is GPU-only; use LTX-2.5 engine or pick 1080p or lower",
        )

    if orientation not in ("landscape", "portrait", "square"):
        raise HTTPException(status_code=400, detail="Invalid orientation")

    if fps not in (24, 25, 30):
        raise HTTPException(status_code=400, detail="FPS must be 24, 25, or 30")

    if output_format not in ("mp4", "webm"):
        raise HTTPException(status_code=400, detail="Output format must be mp4 or webm")

    engine_id = "ltx2" if engine in ("ltx2", "ltx-2.5") else "local"
    caps = {c.engine_id: c for c in list_engines()}
    selected = caps.get(engine_id)
    if not selected or not selected.available:
        raise HTTPException(
            status_code=400,
            detail=(selected.reason if selected else "Unknown engine")
            or "Selected engine is unavailable",
        )

    try:
        scenes_data = json.loads(scenes_json or "[]")
        characters_data = json.loads(characters_json or "[]")
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid scenes_json or characters_json")

    if not isinstance(scenes_data, list) or not isinstance(characters_data, list):
        raise HTTPException(status_code=400, detail="scenes_json and characters_json must be arrays")

    if len(characters_data) > MAX_CHARACTERS:
        raise HTTPException(status_code=400, detail=f"At most {MAX_CHARACTERS} characters")

    # Map uploaded images by index order
    uploads = list(character_images or [])
    if len(uploads) > MAX_CHARACTERS:
        raise HTTPException(status_code=400, detail="Too many character images")

    duration = resolve_duration(length_preset, category, duration_seconds)

    project = VideoProject(
        user_id=current_user.id,
        prompt=prompt.strip(),
        category=category,
        length_preset=length_preset,
        duration_seconds=duration,
        orientation=orientation,
        resolution=resolution,
        fps=fps,
        audio_mode=audio_mode,
        subtitles=bool(subtitles),
        output_format=output_format,
        engine=engine_id,
        status="queued",
        progress=0,
        queue_started_at=datetime.utcnow(),
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # Save characters + images
    for i, char in enumerate(characters_data[:MAX_CHARACTERS]):
        name = (char.get("name") or f"Character {i + 1}").strip()[:200]
        voice_id = (char.get("voice_id") or "en-US-JennyNeural").strip()
        image_path = None
        if i < len(uploads) and uploads[i] is not None:
            upload = uploads[i]
            content_type = (upload.content_type or "").lower()
            if content_type not in ALLOWED_IMAGE_TYPES and not (
                upload.filename or ""
            ).lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                raise HTTPException(status_code=400, detail=f"Invalid image type for character {i + 1}")
            data = await upload.read()
            if len(data) > MAX_IMAGE_BYTES:
                raise HTTPException(status_code=400, detail=f"Character image {i + 1} exceeds 10 MB")
            ext = Path(upload.filename or "img.jpg").suffix.lower() or ".jpg"
            if ext not in (".jpg", ".jpeg", ".png", ".webp"):
                ext = ".jpg"
            dest = CHAR_DIR / f"p{project.id}_c{i}{ext}"
            dest.write_bytes(data)
            image_path = str(dest)
        db.add(
            VideoCharacter(
                project_id=project.id,
                character_index=i,
                name=name,
                voice_id=voice_id,
                image_path=image_path,
            )
        )

    if scenes_data:
        for i, scene in enumerate(scenes_data):
            db.add(
                VideoScene(
                    project_id=project.id,
                    scene_index=i,
                    prompt=(scene.get("prompt") or "").strip() or None,
                    dialogue_text=(scene.get("dialogue_text") or "").strip() or None,
                    character_name=(scene.get("character_name") or "").strip() or None,
                    duration_seconds=scene.get("duration_seconds"),
                )
            )
    else:
        db.add(
            VideoScene(
                project_id=project.id,
                scene_index=0,
                prompt=prompt.strip(),
                dialogue_text=prompt.strip(),
                character_name=characters_data[0]["name"] if characters_data else None,
                duration_seconds=duration,
            )
        )

    db.commit()
    db.refresh(project)

    log_video_event(
        db,
        request,
        action="create",
        user_id=current_user.id,
        project_id=project.id,
        details={
            "category": category,
            "engine": engine_id,
            "duration": duration,
            "characters": len(characters_data),
            "scenes": len(scenes_data) or 1,
        },
        processing_time_ms=int((time.time() - start) * 1000),
    )

    track_usage_event(
        db=db,
        visitor_id=None,
        user_id=current_user.id,
        ip=get_client_ip(request, request.headers.get("X-Forwarded-For")),
        studio="video",
        action="generate",
        tool="text_to_video",
        success=True,
        duration_ms=int((time.time() - start) * 1000),
    )

    enqueue_video_job(project.id)

    project = (
        db.query(VideoProject)
        .options(joinedload(VideoProject.scenes), joinedload(VideoProject.characters))
        .filter(VideoProject.id == project.id)
        .first()
    )
    return _project_to_dict(project)


@router.get("/my")
def list_my_videos(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_studio_access("video")),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
):
    query = db.query(VideoProject).filter(VideoProject.user_id == current_user.id)
    if status:
        query = query.filter(VideoProject.status == status)
    total = query.count()
    items = (
        query.options(joinedload(VideoProject.scenes), joinedload(VideoProject.characters))
        .order_by(desc(VideoProject.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [_project_to_dict(p) for p in items],
    }


@router.get("/{project_id}")
def get_video(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_studio_access("video")),
):
    project = (
        db.query(VideoProject)
        .options(joinedload(VideoProject.scenes), joinedload(VideoProject.characters))
        .filter(VideoProject.id == project_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Video not found")
    if project.user_id != current_user.id and current_user.role != "systemadministrator":
        raise HTTPException(status_code=403, detail="Access denied")
    return _project_to_dict(project)


@router.get("/{project_id}/status")
def get_status(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_studio_access("video")),
):
    project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Video not found")
    if project.user_id != current_user.id and current_user.role != "systemadministrator":
        raise HTTPException(status_code=403, detail="Access denied")
    return {
        "id": project.id,
        "status": project.status,
        "progress": project.progress,
        "error_message": project.error_message,
        "has_output": bool(project.output_path and Path(project.output_path).exists()),
        "stream_url": f"/api/v1/video/{project.id}/stream" if project.output_path else None,
        "thumbnail_url": f"/api/v1/video/{project.id}/thumbnail" if project.thumbnail_path else None,
        "duration_seconds": project.duration_seconds,
    }


def _owned_project(db: Session, project_id: int, user: User) -> VideoProject:
    project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Video not found")
    if project.user_id != user.id and user.role != "systemadministrator":
        raise HTTPException(status_code=403, detail="Access denied")
    return project


def _file_response_with_range(request: Request, path: Path, media_type: str, download_name: str | None = None):
    file_size = path.stat().st_size
    range_header = request.headers.get("range") or request.headers.get("Range")
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(file_size),
    }
    if download_name:
        headers["Content-Disposition"] = f'attachment; filename="{download_name}"'

    if not range_header:
        return FileResponse(path, media_type=media_type, filename=download_name, headers={"Accept-Ranges": "bytes"})

    # bytes=start-end
    try:
        units, _, rng = range_header.partition("=")
        if units.strip() != "bytes":
            raise ValueError("unsupported range")
        start_s, _, end_s = rng.partition("-")
        start = int(start_s) if start_s else 0
        end = int(end_s) if end_s else file_size - 1
        end = min(end, file_size - 1)
        if start > end or start < 0:
            raise ValueError("invalid range")
    except ValueError:
        return Response(status_code=416, headers={"Content-Range": f"bytes */{file_size}"})

    length = end - start + 1

    def iter_file():
        with open(path, "rb") as fh:
            fh.seek(start)
            remaining = length
            while remaining > 0:
                chunk = fh.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    return StreamingResponse(
        iter_file(),
        status_code=206,
        media_type=media_type,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(length),
            **({"Content-Disposition": f'attachment; filename="{download_name}"'} if download_name else {}),
        },
    )


@router.get("/{project_id}/stream")
def stream_video(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_studio_access("video")),
):
    project = _owned_project(db, project_id, current_user)
    path = _resolve_path(project.output_path)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    log_video_event(
        db,
        request,
        action="play",
        user_id=current_user.id,
        project_id=project.id,
        details={"mode": "stream"},
    )
    media_type = mimetypes.guess_type(str(path))[0] or "video/mp4"
    return _file_response_with_range(request, path, media_type)


@router.get("/{project_id}/download")
def download_video(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_studio_access("video")),
):
    project = _owned_project(db, project_id, current_user)
    path = _resolve_path(project.output_path)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Video file not found")
    log_video_event(
        db,
        request,
        action="download",
        user_id=current_user.id,
        project_id=project.id,
    )
    media_type = mimetypes.guess_type(str(path))[0] or "video/mp4"
    return _file_response_with_range(
        request, path, media_type, download_name=f"video_{project.id}{path.suffix}"
    )


@router.get("/{project_id}/thumbnail")
def get_thumbnail(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_studio_access("video")),
):
    project = _owned_project(db, project_id, current_user)
    path = _resolve_path(project.thumbnail_path)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(path, media_type="image/jpeg")


@router.delete("/{project_id}")
def delete_video(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_studio_access("video")),
):
    project = _owned_project(db, project_id, current_user)
    for stored in (project.output_path, project.thumbnail_path):
        path = _resolve_path(stored)
        if path and path.exists() and VIDEO_DIR in path.resolve().parents:
            try:
                path.unlink()
            except OSError:
                pass
    for char in project.characters or []:
        path = _resolve_path(char.image_path)
        if path and path.exists():
            try:
                path.unlink()
            except OSError:
                pass
    log_video_event(
        db,
        request,
        action="delete",
        user_id=current_user.id,
        project_id=project.id,
    )
    db.delete(project)
    db.commit()
    return {"message": "Deleted"}


@router.post("/events")
def client_log_event(
    request: Request,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Frontend play/download/etc logging helper."""
    action = str(payload.get("action") or "client_event")
    log_video_event(
        db,
        request,
        action=action,
        user_id=current_user.id,
        project_id=payload.get("project_id"),
        details=payload.get("details"),
        status=str(payload.get("status") or "success"),
    )
    return {"ok": True}
