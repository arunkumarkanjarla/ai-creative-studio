"""
Admin Video Studio APIs — require_admin.
"""
from __future__ import annotations

import csv
import io
import mimetypes
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import asc, desc, func, or_
from sqlalchemy.orm import Session, joinedload

from app.api.v1.dependencies import require_admin
from app.core.video_events import log_video_event
from app.db.database import get_db
from app.models.user import User
from app.models.video import VideoProject
from app.models.video_events import VideoEvent

router = APIRouter(prefix="/admin/video", tags=["Admin Video"])

BACKEND_DIR = Path(__file__).resolve().parents[3]
VIDEO_DIR = BACKEND_DIR / "generated_videos"


def resolve_video_path(stored: str | None) -> Path | None:
    if not stored:
        return None
    path = Path(stored)
    if path.is_absolute():
        return path
    return VIDEO_DIR / stored.lstrip("/")


def _user_info(db: Session, user_id: int | None) -> dict | None:
    if not user_id:
        return None
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"type": "user", "id": user_id}
    return {"type": "user", "id": user.id, "name": user.name, "email": user.email}


@router.get("/overview")
def overview(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    days: int = Query(7, ge=1, le=90),
):
    since = datetime.utcnow() - timedelta(days=days)
    total = db.query(func.count(VideoProject.id)).scalar() or 0
    completed = (
        db.query(func.count(VideoProject.id))
        .filter(VideoProject.status == "completed")
        .scalar()
        or 0
    )
    failed = (
        db.query(func.count(VideoProject.id)).filter(VideoProject.status == "failed").scalar()
        or 0
    )
    queued = (
        db.query(func.count(VideoProject.id))
        .filter(VideoProject.status.in_(["queued", "processing"]))
        .scalar()
        or 0
    )
    avg_render = (
        db.query(func.avg(VideoProject.generation_time_seconds))
        .filter(VideoProject.status == "completed")
        .scalar()
    )
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = (
        db.query(func.count(VideoProject.id))
        .filter(VideoProject.created_at >= today_start)
        .scalar()
        or 0
    )

    # Per day
    per_day_rows = (
        db.query(func.date(VideoProject.created_at), func.count(VideoProject.id))
        .filter(VideoProject.created_at >= since)
        .group_by(func.date(VideoProject.created_at))
        .order_by(func.date(VideoProject.created_at))
        .all()
    )
    by_category = (
        db.query(VideoProject.category, func.count(VideoProject.id))
        .filter(VideoProject.created_at >= since)
        .group_by(VideoProject.category)
        .all()
    )
    by_engine = (
        db.query(VideoProject.engine, func.count(VideoProject.id))
        .filter(VideoProject.created_at >= since)
        .group_by(VideoProject.engine)
        .all()
    )
    success_fail = (
        db.query(VideoProject.status, func.count(VideoProject.id))
        .filter(
            VideoProject.created_at >= since,
            VideoProject.status.in_(["completed", "failed"]),
        )
        .group_by(VideoProject.status)
        .all()
    )
    top_users = (
        db.query(
            VideoProject.user_id,
            func.count(VideoProject.id),
            User.name,
            User.email,
        )
        .outerjoin(User, User.id == VideoProject.user_id)
        .filter(VideoProject.created_at >= since)
        .group_by(VideoProject.user_id, User.name, User.email)
        .order_by(desc(func.count(VideoProject.id)))
        .limit(10)
        .all()
    )

    return {
        "summary": {
            "total_videos": total,
            "completed": completed,
            "failed": failed,
            "queued_or_processing": queued,
            "today_count": today_count,
            "avg_render_seconds": round(float(avg_render or 0), 2),
        },
        "videos_per_day": [
            {"date": str(d), "count": c} for d, c in per_day_rows
        ],
        "by_category": [{"category": c or "unknown", "count": n} for c, n in by_category],
        "by_engine": [{"engine": e or "unknown", "count": n} for e, n in by_engine],
        "success_failure": [{"status": s, "count": n} for s, n in success_fail],
        "top_users": [
            {
                "user_id": uid,
                "name": name,
                "email": email,
                "count": count,
            }
            for uid, count, name, email in top_users
        ],
    }


@router.get("/generated/list")
def list_generated(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    category: Optional[str] = None,
    engine: Optional[str] = None,
    status: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    sort_by: str = Query("created_at"),
    sort_order: str = Query("desc"),
):
    query = db.query(VideoProject)
    if search:
        query = query.filter(VideoProject.prompt.ilike(f"%{search}%"))
    if category:
        query = query.filter(VideoProject.category == category)
    if engine:
        query = query.filter(VideoProject.engine == engine)
    if status:
        query = query.filter(VideoProject.status == status)
    if date_from:
        try:
            query = query.filter(VideoProject.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(VideoProject.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    total = query.count()
    sort_col = getattr(VideoProject, sort_by, VideoProject.created_at)
    query = query.order_by(desc(sort_col) if sort_order == "desc" else asc(sort_col))
    items = (
        query.options(joinedload(VideoProject.scenes), joinedload(VideoProject.characters))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    results = []
    for item in items:
        out = resolve_video_path(item.output_path)
        results.append(
            {
                "id": item.id,
                "user": _user_info(db, item.user_id),
                "prompt_preview": (item.prompt or "")[:120],
                "prompt": item.prompt,
                "category": item.category,
                "engine": item.engine,
                "orientation": item.orientation,
                "resolution": item.resolution,
                "duration": item.duration_seconds,
                "file_size": item.file_size_bytes,
                "status": item.status,
                "progress": item.progress,
                "created_at": item.created_at.isoformat() if item.created_at else None,
                "file_exists": bool(out and out.exists()),
                "stream_url": f"/api/v1/admin/video/generated/{item.id}/stream",
                "download_url": f"/api/v1/admin/video/generated/{item.id}/download",
                "thumbnail_url": f"/api/v1/admin/video/generated/{item.id}/thumbnail",
                "scenes": len(item.scenes or []),
                "characters": len(item.characters or []),
            }
        )
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if limit else 0,
        "items": results,
    }


@router.get("/generated/{project_id}/stream")
def admin_stream(project_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Not found")
    path = resolve_video_path(project.output_path)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="File missing")
    return FileResponse(path, media_type=mimetypes.guess_type(str(path))[0] or "video/mp4")


@router.get("/generated/{project_id}/download")
def admin_download(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Not found")
    path = resolve_video_path(project.output_path)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="File missing")
    log_video_event(
        db, request, action="download", user_id=admin.id, project_id=project.id, details={"admin": True}
    )
    return FileResponse(
        path,
        media_type=mimetypes.guess_type(str(path))[0] or "video/mp4",
        filename=f"video_{project.id}{path.suffix}",
    )


@router.get("/generated/{project_id}/thumbnail")
def admin_thumb(project_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)):
    project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Not found")
    path = resolve_video_path(project.thumbnail_path)
    if not path or not path.exists():
        raise HTTPException(status_code=404, detail="Thumbnail missing")
    return FileResponse(path, media_type="image/jpeg")


@router.delete("/generated/{project_id}")
def admin_delete(
    project_id: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Not found")
    for stored in (project.output_path, project.thumbnail_path):
        path = resolve_video_path(stored)
        if path and path.exists():
            try:
                path.unlink()
            except OSError:
                pass
    log_video_event(
        db, request, action="delete", user_id=admin.id, project_id=project.id, details={"admin": True}
    )
    db.delete(project)
    db.commit()
    return {"message": "Deleted"}


@router.post("/generated/bulk-delete")
def admin_bulk_delete(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    ids = payload.get("ids") or payload.get("project_ids") or []
    deleted = 0
    for pid in ids:
        project = db.query(VideoProject).filter(VideoProject.id == int(pid)).first()
        if not project:
            continue
        for stored in (project.output_path, project.thumbnail_path):
            path = resolve_video_path(stored)
            if path and path.exists():
                try:
                    path.unlink()
                except OSError:
                    pass
        log_video_event(
            db, request, action="delete", user_id=admin.id, project_id=project.id, details={"admin": True, "bulk": True}
        )
        db.delete(project)
        deleted += 1
    db.commit()
    return {"deleted": deleted}


@router.get("/generated/export")
def export_csv(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    search: Optional[str] = None,
    category: Optional[str] = None,
    engine: Optional[str] = None,
    status: Optional[str] = None,
):
    query = db.query(VideoProject)
    if search:
        query = query.filter(VideoProject.prompt.ilike(f"%{search}%"))
    if category:
        query = query.filter(VideoProject.category == category)
    if engine:
        query = query.filter(VideoProject.engine == engine)
    if status:
        query = query.filter(VideoProject.status == status)
    items = query.order_by(desc(VideoProject.created_at)).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "ID",
            "User ID",
            "Category",
            "Engine",
            "Status",
            "Duration",
            "Resolution",
            "Orientation",
            "File Size",
            "Created At",
            "Prompt",
        ]
    )
    for item in items:
        writer.writerow(
            [
                item.id,
                item.user_id,
                item.category,
                item.engine,
                item.status,
                item.duration_seconds,
                item.resolution,
                item.orientation,
                item.file_size_bytes,
                item.created_at.isoformat() if item.created_at else "",
                (item.prompt or "")[:200],
            ]
        )
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename=videos_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        },
    )


@router.get("/jobs")
def jobs_queue(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    items = (
        db.query(VideoProject)
        .filter(VideoProject.status.in_(["queued", "processing"]))
        .order_by(VideoProject.created_at.asc())
        .all()
    )
    return {
        "items": [
            {
                "id": p.id,
                "user": _user_info(db, p.user_id),
                "status": p.status,
                "progress": p.progress,
                "engine": p.engine,
                "category": p.category,
                "prompt_preview": (p.prompt or "")[:100],
                "created_at": p.created_at.isoformat() if p.created_at else None,
                "processing_started_at": (
                    p.processing_started_at.isoformat() if p.processing_started_at else None
                ),
            }
            for p in items
        ]
    }


@router.get("/users")
def users_stats(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    stats = (
        db.query(
            VideoProject.user_id,
            User.name,
            User.email,
            func.count(VideoProject.id).label("total"),
            func.sum(VideoProject.file_size_bytes).label("total_size"),
            func.avg(VideoProject.generation_time_seconds).label("avg_render"),
        )
        .outerjoin(User, User.id == VideoProject.user_id)
        .group_by(VideoProject.user_id, User.name, User.email)
        .order_by(desc(func.count(VideoProject.id)))
        .all()
    )
    items = []
    for uid, name, email, total, total_size, avg_render in stats:
        completed = (
            db.query(func.count(VideoProject.id))
            .filter(VideoProject.user_id == uid, VideoProject.status == "completed")
            .scalar()
            or 0
        )
        failed = (
            db.query(func.count(VideoProject.id))
            .filter(VideoProject.user_id == uid, VideoProject.status == "failed")
            .scalar()
            or 0
        )
        items.append(
            {
                "user_id": uid,
                "name": name,
                "email": email,
                "total": total,
                "completed": completed,
                "failed": failed,
                "total_size": int(total_size or 0),
                "avg_render_seconds": round(float(avg_render or 0), 2),
            }
        )
    return {"items": items}


@router.get("/events")
def event_log(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    action: Optional[str] = None,
    status: Optional[str] = None,
    user_id: Optional[int] = None,
    search: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    query = db.query(VideoEvent)
    if action:
        query = query.filter(VideoEvent.action == action)
    if status:
        query = query.filter(VideoEvent.status == status)
    if user_id:
        query = query.filter(VideoEvent.user_id == user_id)
    if search:
        query = query.filter(
            or_(
                VideoEvent.error_message.ilike(f"%{search}%"),
                VideoEvent.user_agent.ilike(f"%{search}%"),
            )
        )
    if date_from:
        try:
            query = query.filter(VideoEvent.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            query = query.filter(VideoEvent.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass
    total = query.count()
    events = (
        query.order_by(desc(VideoEvent.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [
            {
                "id": e.id,
                "user": _user_info(db, e.user_id),
                "action": e.action,
                "status": e.status,
                "project_id": e.project_id,
                "details": e.details,
                "error_message": e.error_message,
                "processing_time_ms": e.processing_time_ms,
                "duration_seconds": e.duration_seconds,
                "ip_address": str(e.ip_address) if e.ip_address else None,
                "browser": e.browser,
                "os": e.os,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in events
        ],
    }


@router.get("/events/export")
def export_events(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    action: Optional[str] = None,
    status: Optional[str] = None,
):
    query = db.query(VideoEvent)
    if action:
        query = query.filter(VideoEvent.action == action)
    if status:
        query = query.filter(VideoEvent.status == status)
    events = query.order_by(desc(VideoEvent.created_at)).limit(5000).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        ["ID", "User ID", "Action", "Status", "Project ID", "Error", "Created At"]
    )
    for e in events:
        writer.writerow(
            [
                e.id,
                e.user_id,
                e.action,
                e.status,
                e.project_id,
                e.error_message or "",
                e.created_at.isoformat() if e.created_at else "",
            ]
        )
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename=video_events_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        },
    )


@router.get("/errors")
def failed_errors(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
):
    query = db.query(VideoProject).filter(VideoProject.status == "failed")
    total = query.count()
    items = (
        query.order_by(desc(VideoProject.created_at))
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "items": [
            {
                "id": p.id,
                "user": _user_info(db, p.user_id),
                "prompt_preview": (p.prompt or "")[:120],
                "engine": p.engine,
                "category": p.category,
                "error_message": p.error_message,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in items
        ],
    }
