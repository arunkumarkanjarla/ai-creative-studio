from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import func, case, extract
from sqlalchemy.orm import Session
import csv
import io

from app.api.v1.dependencies import get_current_user, require_admin
from app.db.database import get_db
from app.models.user import User
from app.models.analytics import VisitorSession, LoginSession, UsageEvent
from app.models.audio_events import AudioEvent
from app.core.analytics import track_page_visit, get_client_ip

router = APIRouter(prefix="/analytics", tags=["Analytics"])




@router.post("/track")
def track_frontend_view(
    request: Request,
    path: str,
    action: Optional[str] = None,
    studio: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Track a frontend page view (works for anonymous users)."""
    visitor_id = request.headers.get("X-Visitor-Id", "unknown")
    user_agent = request.headers.get("User-Agent")
    ip = get_client_ip(request, request.headers.get("X-Forwarded-For"))
    
    # Try to get user ID from auth token if present
    user_id = None
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            from app.core.security import decode_token
            payload = decode_token(token)
            user_id = int(payload.get("sub")) if payload.get("sub") else None
        except Exception:
            pass
    
    track_page_visit(db, visitor_id, user_id, ip, user_agent, path, studio)
    return {"status": "tracked"}


@router.get("/summary")
def get_analytics_summary(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    granularity: str = Query("day", regex="^(day|week|month|year)$"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Get analytics summary for date range."""
    
    # Calculate previous period for comparison
    duration = end_date - start_date
    prev_start = start_date - duration
    prev_end = start_date
    
    # Current period metrics
    unique_ips = db.query(func.count(func.distinct(VisitorSession.ip_address)))\
        .filter(VisitorSession.created_at.between(start_date, end_date))\
        .scalar() or 0
    
    unique_users = db.query(func.count(func.distinct(VisitorSession.user_id)))\
        .filter(VisitorSession.user_id.isnot(None))\
        .filter(VisitorSession.created_at.between(start_date, end_date))\
        .scalar() or 0
    
    unique_visitors = db.query(func.count(func.distinct(VisitorSession.visitor_id)))\
        .filter(VisitorSession.created_at.between(start_date, end_date))\
        .scalar() or 0
    
    total_visits = db.query(func.count(VisitorSession.id))\
        .filter(VisitorSession.created_at.between(start_date, end_date))\
        .scalar() or 0
    
    logins_success = db.query(func.count(LoginSession.id))\
        .filter(LoginSession.status == "success")\
        .filter(LoginSession.login_at.between(start_date, end_date))\
        .scalar() or 0
    
    logins_failed = db.query(func.count(LoginSession.id))\
        .filter(LoginSession.status == "failed")\
        .filter(LoginSession.login_at.between(start_date, end_date))\
        .scalar() or 0
    
    generations = db.query(func.count(UsageEvent.id))\
        .filter(UsageEvent.action == "generate")\
        .filter(UsageEvent.created_at.between(start_date, end_date))\
        .scalar() or 0
    
    # Previous period metrics for comparison
    prev_unique_ips = db.query(func.count(func.distinct(VisitorSession.ip_address)))\
        .filter(VisitorSession.created_at.between(prev_start, prev_end))\
        .scalar() or 0
    
    prev_unique_users = db.query(func.count(func.distinct(VisitorSession.user_id)))\
        .filter(VisitorSession.user_id.isnot(None))\
        .filter(VisitorSession.created_at.between(prev_start, prev_end))\
        .scalar() or 0
    
    prev_logins_success = db.query(func.count(LoginSession.id))\
        .filter(LoginSession.status == "success")\
        .filter(LoginSession.login_at.between(prev_start, prev_end))\
        .scalar() or 0
    
    # Per-studio usage
    studio_usage = db.query(
        UsageEvent.studio,
        func.count(UsageEvent.id).label("count")
    ).filter(
        UsageEvent.created_at.between(start_date, end_date)
    ).group_by(UsageEvent.studio).all()
    
    # Device/browser split
    device_split = db.query(
        VisitorSession.device_type,
        func.count(VisitorSession.id).label("count")
    ).filter(
        VisitorSession.created_at.between(start_date, end_date)
    ).group_by(VisitorSession.device_type).all()
    
    browser_split = db.query(
        VisitorSession.browser.label("browser"),
        func.count(VisitorSession.id).label("count")
    ).filter(
        VisitorSession.created_at.between(start_date, end_date)
    ).filter(VisitorSession.browser.isnot(None))\
    .group_by(VisitorSession.browser)\
    .order_by(func.count(VisitorSession.id).desc())\
    .limit(10).all()
    
    # Top IPs
    top_ips = db.query(
        VisitorSession.ip_address,
        func.count(VisitorSession.id).label("visits")
    ).filter(
        VisitorSession.created_at.between(start_date, end_date)
    ).group_by(VisitorSession.ip_address)\
    .order_by(func.count(VisitorSession.id).desc())\
    .limit(10).all()
    
    # Top users
    top_users = db.query(
        User.email,
        func.count(VisitorSession.id).label("visits")
    ).join(VisitorSession, User.id == VisitorSession.user_id)\
    .filter(VisitorSession.created_at.between(start_date, end_date))\
    .group_by(User.email)\
    .order_by(func.count(VisitorSession.id).desc())\
    .limit(10).all()
    
    return {
        "summary": {
            "unique_ips": unique_ips,
            "unique_users": unique_users,
            "unique_visitors": unique_visitors,
            "total_visits": total_visits,
            "logins_success": logins_success,
            "logins_failed": logins_failed,
            "generations": generations,
        },
        "changes": {
            "unique_ips": unique_ips - prev_unique_ips,
            "unique_users": unique_users - prev_unique_users,
            "logins_success": logins_success - prev_logins_success,
        },
        "studio_usage": [{"studio": s or "other", "count": c} for s, c in studio_usage],
        "device_split": [{"device": d or "unknown", "count": c} for d, c in device_split],
        "browser_split": [{"browser": b or "unknown", "count": c} for b, c in browser_split],
        "top_ips": [{"ip": ip, "visits": v} for ip, v in top_ips],
        "top_users": [{"email": e, "visits": v} for e, v in top_users],
    }


@router.get("/timeseries")
def get_timeseries_data(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    granularity: str = Query("day", regex="^(day|week|month|year)$"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Get time series data for charts."""
    
    # Determine date trunc format
    trunc_format = {
        "day": "day",
        "week": "week",
        "month": "month",
        "year": "year",
    }[granularity]
    
    # Visitors over time (logged-in vs guest)
    visitors_ts = db.query(
        func.date_trunc(trunc_format, VisitorSession.created_at).label("period"),
        func.count(case((VisitorSession.user_id.isnot(None), 1))).label("logged_in"),
        func.count(case((VisitorSession.user_id.is_(None), 1))).label("guest"),
    ).filter(
        VisitorSession.created_at.between(start_date, end_date)
    ).group_by("period").order_by("period").all()
    
    # Per-studio usage over time
    studio_ts = db.query(
        func.date_trunc(trunc_format, UsageEvent.created_at).label("period"),
        UsageEvent.studio,
        func.count(UsageEvent.id).label("count")
    ).filter(
        UsageEvent.created_at.between(start_date, end_date)
    ).filter(UsageEvent.studio.isnot(None))\
    .group_by("period", UsageEvent.studio)\
    .order_by("period").all()
    
    return {
        "visitors": [
            {
                "period": p.isoformat(),
                "logged_in": logged_in,
                "guest": guest,
            }
            for p, logged_in, guest in visitors_ts
        ],
        "studio_usage": [
            {
                "period": p.isoformat(),
                "studio": studio,
                "count": count,
            }
            for p, studio, count in studio_ts
        ],
    }


@router.get("/hourly-breakdown")
def get_hourly_breakdown(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    tz_offset_minutes: int = Query(0, description="Timezone offset in minutes from UTC (e.g., -300 for EST)"),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Get weekday x hour activity heatmap data. Timezone offset applied in SQL."""
    from sqlalchemy import text
    
    # Calculate activity by weekday (0=Sunday, 1=Monday, ..., 6=Saturday) and hour (0-23)
    # Apply timezone offset by building the SQL dynamically with the validated integer parameter
    # Safe because tz_offset_minutes is an integer query parameter validated by FastAPI
    query_sql = f"""
        SELECT 
            EXTRACT(DOW FROM created_at + INTERVAL '{tz_offset_minutes} minutes')::INTEGER as weekday,
            EXTRACT(HOUR FROM created_at + INTERVAL '{tz_offset_minutes} minutes')::INTEGER as hour,
            COUNT(*) as count
        FROM visitor_sessions
        WHERE created_at BETWEEN :start_date AND :end_date
        GROUP BY weekday, hour
        ORDER BY weekday, hour
    """
    
    query = text(query_sql)
    
    result = db.execute(query, {
        "start_date": start_date,
        "end_date": end_date,
    })
    
    heatmap_data = [
        {"weekday": int(row[0]), "hour": int(row[1]), "count": int(row[2])}
        for row in result
    ]
    
    # Calculate peak hours (top 3 hours with most activity)
    hourly_totals = {}
    for item in heatmap_data:
        hour = item["hour"]
        hourly_totals[hour] = hourly_totals.get(hour, 0) + item["count"]
    
    peak_hours = sorted(hourly_totals.items(), key=lambda x: x[1], reverse=True)[:3]
    
    return {
        "heatmap": heatmap_data,
        "peak_hours": [{"hour": h, "count": c} for h, c in peak_hours],
        "total_visits": sum(item["count"] for item in heatmap_data)
    }


@router.get("/login-history")
def get_login_history(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, le=200),
    user_email: Optional[str] = None,
    ip: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Get paginated login session history with filters."""
    
    query = db.query(LoginSession).join(User, LoginSession.user_id == User.id, isouter=True)
    
    if user_email:
        query = query.filter(User.email.ilike(f"%{user_email}%"))
    if ip:
        query = query.filter(LoginSession.ip_address.ilike(f"%{ip}%"))
    if status:
        query = query.filter(LoginSession.status == status)
    if start_date:
        query = query.filter(LoginSession.login_at >= start_date)
    if end_date:
        query = query.filter(LoginSession.login_at <= end_date)
    
    total = query.count()
    sessions = query.order_by(LoginSession.login_at.desc()).offset(skip).limit(limit).all()
    
    items = []
    for session in sessions:
        user_email_val = db.query(User.email).filter(User.id == session.user_id).scalar() if session.user_id else None
        items.append({
            "id": session.id,
            "user_email": user_email_val,
            "username_attempted": session.username_attempted,
            "ip": session.ip_address,
            "browser": session.browser,
            "device_type": session.device_type,
            "login_at": session.login_at.isoformat() if session.login_at else None,
            "status": session.status,
            "failure_reason": session.failure_reason,
        })
    
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "items": items,
    }


@router.get("/export/csv")
def export_analytics_csv(
    start_date: datetime = Query(...),
    end_date: datetime = Query(...),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Export analytics data as CSV."""
    
    sessions = db.query(VisitorSession).filter(
        VisitorSession.created_at.between(start_date, end_date)
    ).order_by(VisitorSession.created_at.desc()).limit(10000).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Visitor ID", "User ID", "IP", "Browser", "Device", "Path", "Studio"])
    
    for s in sessions:
        writer.writerow([
            s.created_at.isoformat() if s.created_at else "",
            s.visitor_id,
            s.user_id or "",
            s.ip_address,
            s.browser or "",
            s.device_type or "",
            s.path or "",
            s.studio or "",
        ])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=analytics_{start_date.date()}_{end_date.date()}.csv"}
    )


@router.get("/login-history/export")
def export_login_history_csv(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    user_email: Optional[str] = None,
    ip: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Export login history as CSV."""
    
    query = db.query(LoginSession).join(User, LoginSession.user_id == User.id, isouter=True)
    
    if user_email:
        query = query.filter(User.email.ilike(f"%{user_email}%"))
    if ip:
        query = query.filter(LoginSession.ip_address.ilike(f"%{ip}%"))
    if status:
        query = query.filter(LoginSession.status == status)
    if start_date:
        query = query.filter(LoginSession.login_at >= start_date)
    if end_date:
        query = query.filter(LoginSession.login_at <= end_date)
    
    sessions = query.order_by(LoginSession.login_at.desc()).limit(10000).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Login Time", "User Email", "Username Attempted", "IP", "Browser", "Device", "Status", "Failure Reason", "Logout Time", "Duration (s)"])
    
    for s in sessions:
        user_email_val = db.query(User.email).filter(User.id == s.user_id).scalar() if s.user_id else ""
        writer.writerow([
            s.login_at.isoformat() if s.login_at else "",
            user_email_val,
            s.username_attempted or "",
            s.ip_address,
            s.browser or "",
            s.device_type or "",
            s.status,
            s.failure_reason or "",
            s.logout_at.isoformat() if s.logout_at else "",
            s.duration or "",
        ])
    
    output.seek(0)
    filename = f"login_history_{datetime.now().date()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================== AUDIO ANALYTICS ====================

@router.get("/audio/summary")
def get_audio_analytics_summary(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Get audio analytics summary and charts data."""
    
    # Apply date filters
    query = db.query(AudioEvent)
    if start_date:
        query = query.filter(AudioEvent.created_at >= start_date)
    if end_date:
        query = query.filter(AudioEvent.created_at <= end_date)
    
    # Total events
    total_events = query.count()
    
    # Success vs failed
    success_count = query.filter(AudioEvent.status == "success").count()
    failed_count = query.filter(AudioEvent.status == "failed").count()
    rate_limited_count = query.filter(AudioEvent.status == "rate_limited").count()
    
    # TTS vs STT (by generate and transcribe actions)
    tts_count = query.filter(AudioEvent.action == "generate").count()
    stt_count = query.filter(AudioEvent.action == "transcribe").count()
    play_count = query.filter(AudioEvent.action == "play").count()
    download_count = query.filter(AudioEvent.action == "download").count()
    
    # Signed-in vs guest
    authenticated_count = query.filter(AudioEvent.user_id.isnot(None)).count()
    guest_count = query.filter(AudioEvent.user_id.is_(None)).count()
    
    # Unique users and visitors
    unique_users = db.query(func.count(func.distinct(AudioEvent.user_id)))\
        .filter(AudioEvent.user_id.isnot(None))
    if start_date:
        unique_users = unique_users.filter(AudioEvent.created_at >= start_date)
    if end_date:
        unique_users = unique_users.filter(AudioEvent.created_at <= end_date)
    unique_users = unique_users.scalar() or 0
    
    unique_visitors = db.query(func.count(func.distinct(AudioEvent.visitor_id)))\
        .filter(AudioEvent.user_id.is_(None), AudioEvent.visitor_id.isnot(None))
    if start_date:
        unique_visitors = unique_visitors.filter(AudioEvent.created_at >= start_date)
    if end_date:
        unique_visitors = unique_visitors.filter(AudioEvent.created_at <= end_date)
    unique_visitors = unique_visitors.scalar() or 0
    
    # Total characters processed (TTS)
    total_chars = db.query(func.sum(AudioEvent.text_length))\
        .filter(AudioEvent.action == "generate", AudioEvent.status == "success")
    if start_date:
        total_chars = total_chars.filter(AudioEvent.created_at >= start_date)
    if end_date:
        total_chars = total_chars.filter(AudioEvent.created_at <= end_date)
    total_chars = total_chars.scalar() or 0
    
    # Total audio minutes processed
    total_minutes = db.query(func.sum(AudioEvent.audio_duration))\
        .filter(AudioEvent.status == "success", AudioEvent.audio_duration.isnot(None))
    if start_date:
        total_minutes = total_minutes.filter(AudioEvent.created_at >= start_date)
    if end_date:
        total_minutes = total_minutes.filter(AudioEvent.created_at <= end_date)
    total_minutes = (total_minutes.scalar() or 0) / 60  # Convert to minutes
    
    # Top voices
    top_voices_query = db.query(
        AudioEvent.voice_name,
        func.count(AudioEvent.id).label("count")
    ).filter(
        AudioEvent.action == "generate",
        AudioEvent.status == "success",
        AudioEvent.voice_name.isnot(None)
    )
    if start_date:
        top_voices_query = top_voices_query.filter(AudioEvent.created_at >= start_date)
    if end_date:
        top_voices_query = top_voices_query.filter(AudioEvent.created_at <= end_date)
    top_voices = top_voices_query.group_by(AudioEvent.voice_name)\
        .order_by(func.count(AudioEvent.id).desc())\
        .limit(10)\
        .all()
    
    # Top languages
    top_languages_query = db.query(
        AudioEvent.language,
        func.count(AudioEvent.id).label("count")
    ).filter(
        AudioEvent.language.isnot(None),
        AudioEvent.status == "success"
    )
    if start_date:
        top_languages_query = top_languages_query.filter(AudioEvent.created_at >= start_date)
    if end_date:
        top_languages_query = top_languages_query.filter(AudioEvent.created_at <= end_date)
    top_languages = top_languages_query.group_by(AudioEvent.language)\
        .order_by(func.count(AudioEvent.id).desc())\
        .limit(10)\
        .all()
    
    # Time series data (daily)
    time_series_query = db.query(
        func.date(AudioEvent.created_at).label("date"),
        func.count(case((AudioEvent.action == "generate", 1))).label("tts_count"),
        func.count(case((AudioEvent.action == "transcribe", 1))).label("stt_count"),
        func.count(case((AudioEvent.user_id.isnot(None), 1))).label("authenticated_count"),
        func.count(case((AudioEvent.user_id.is_(None), 1))).label("guest_count")
    )
    if start_date:
        time_series_query = time_series_query.filter(AudioEvent.created_at >= start_date)
    if end_date:
        time_series_query = time_series_query.filter(AudioEvent.created_at <= end_date)
    time_series = time_series_query.group_by(func.date(AudioEvent.created_at))\
        .order_by(func.date(AudioEvent.created_at))\
        .all()
    
    return {
        "summary": {
            "total_events": total_events,
            "success_count": success_count,
            "failed_count": failed_count,
            "rate_limited_count": rate_limited_count,
            "tts_count": tts_count,
            "stt_count": stt_count,
            "play_count": play_count,
            "download_count": download_count,
            "authenticated_count": authenticated_count,
            "guest_count": guest_count,
            "unique_users": unique_users,
            "unique_visitors": unique_visitors,
            "total_characters": int(total_chars),
            "total_minutes": round(total_minutes, 2)
        },
        "top_voices": [{"name": v[0], "count": v[1]} for v in top_voices],
        "top_languages": [{"name": l[0], "count": l[1]} for l in top_languages],
        "time_series": [
            {
                "date": ts[0].isoformat() if ts[0] else None,
                "tts_count": ts[1],
                "stt_count": ts[2],
                "authenticated_count": ts[3],
                "guest_count": ts[4]
            }
            for ts in time_series
        ]
    }


@router.get("/audio/events")
def get_audio_events_log(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user_type: Optional[str] = Query(None, regex="^(authenticated|guest)$"),
    user_id: Optional[int] = Query(None),
    visitor_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    voice_name: Optional[str] = Query(None),
    language: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Get filterable audio events log with pagination."""
    
    query = db.query(AudioEvent)
    
    # Apply filters
    if start_date:
        query = query.filter(AudioEvent.created_at >= start_date)
    if end_date:
        query = query.filter(AudioEvent.created_at <= end_date)
    if user_type == "authenticated":
        query = query.filter(AudioEvent.user_id.isnot(None))
    elif user_type == "guest":
        query = query.filter(AudioEvent.user_id.is_(None))
    if user_id:
        query = query.filter(AudioEvent.user_id == user_id)
    if visitor_id:
        query = query.filter(AudioEvent.visitor_id == visitor_id)
    if action:
        query = query.filter(AudioEvent.action == action)
    if status:
        query = query.filter(AudioEvent.status == status)
    if voice_name:
        query = query.filter(AudioEvent.voice_name.ilike(f"%{voice_name}%"))
    if language:
        query = query.filter(AudioEvent.language == language)
    if search:
        query = query.filter(
            (AudioEvent.input_text.ilike(f"%{search}%")) |
            (AudioEvent.voice_name.ilike(f"%{search}%")) |
            (AudioEvent.error_message.ilike(f"%{search}%"))
        )
    
    total = query.count()
    events = query.order_by(AudioEvent.created_at.desc()).offset(offset).limit(limit).all()
    
    # Get user emails for authenticated events
    user_ids = [e.user_id for e in events if e.user_id]
    users_map = {}
    if user_ids:
        users = db.query(User.id, User.email, User.username).filter(User.id.in_(user_ids)).all()
        users_map = {u.id: {"email": u.email, "username": u.username} for u in users}
    
    return {
        "total": total,
        "items": [
            {
                "id": e.id,
                "user_id": e.user_id,
                "user_email": users_map.get(e.user_id, {}).get("email") if e.user_id else None,
                "user_name": users_map.get(e.user_id, {}).get("username") if e.user_id else None,
                "visitor_id": e.visitor_id,
                "ip_address": str(e.ip_address) if e.ip_address else None,
                "user_agent": e.user_agent,
                "browser": e.browser,
                "os": e.os,
                "device": e.device,
                "action": e.action,
                "studio": e.studio,
                "voice_id": e.voice_id,
                "voice_name": e.voice_name,
                "language": e.language,
                "text_length": e.text_length,
                "input_text": e.input_text,
                "audio_duration": e.audio_duration,
                "file_size": e.file_size,
                "processing_time_ms": e.processing_time_ms,
                "status": e.status,
                "error_message": e.error_message,
                "generation_id": e.generation_id,
                "transcription_id": e.transcription_id,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in events
        ]
    }


@router.get("/audio/users")
def get_audio_users_list(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user_type: Optional[str] = Query(None, regex="^(authenticated|guest)$"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Get users and guests list with their audio activity stats."""
    
    # Build base query filters
    filters = []
    if start_date:
        filters.append(AudioEvent.created_at >= start_date)
    if end_date:
        filters.append(AudioEvent.created_at <= end_date)
    
    results = []
    
    # Get authenticated users stats
    if user_type != "guest":
        users_query = db.query(
            AudioEvent.user_id,
            func.min(AudioEvent.created_at).label("first_seen"),
            func.max(AudioEvent.created_at).label("last_seen"),
            func.count(case((AudioEvent.action == "generate", 1))).label("tts_count"),
            func.count(case((AudioEvent.action == "transcribe", 1))).label("stt_count"),
            func.count(case((AudioEvent.action == "play", 1))).label("play_count"),
            func.count(case((AudioEvent.action == "download", 1))).label("download_count"),
            func.sum(AudioEvent.text_length).label("total_chars"),
            func.sum(AudioEvent.audio_duration).label("total_duration"),
            func.array_agg(func.distinct(AudioEvent.voice_name)).label("top_voices"),
            func.array_agg(func.distinct(AudioEvent.language)).label("languages")
        ).filter(AudioEvent.user_id.isnot(None), *filters)\
        .group_by(AudioEvent.user_id)\
        .order_by(func.max(AudioEvent.created_at).desc())\
        .offset(offset).limit(limit).all()
        
        # Get user details
        user_ids = [u.user_id for u in users_query]
        if user_ids:
            users_map = {}
            users = db.query(User).filter(User.id.in_(user_ids)).all()
            users_map = {u.id: u for u in users}
            
            for u in users_query:
                user = users_map.get(u.user_id)
                results.append({
                    "user_type": "authenticated",
                    "user_id": u.user_id,
                    "user_email": user.email if user else None,
                    "user_name": user.username if user else None,
                    "visitor_id": None,
                    "ip_address": None,
                    "first_seen": u.first_seen.isoformat() if u.first_seen else None,
                    "last_seen": u.last_seen.isoformat() if u.last_seen else None,
                    "tts_count": u.tts_count or 0,
                    "stt_count": u.stt_count or 0,
                    "play_count": u.play_count or 0,
                    "download_count": u.download_count or 0,
                    "total_characters": int(u.total_chars or 0),
                    "total_minutes": round((u.total_duration or 0) / 60, 2),
                    "top_voices": [v for v in (u.top_voices or []) if v],
                    "languages": [l for l in (u.languages or []) if l]
                })
    
    # Get guest stats
    if user_type != "authenticated":
        guests_query = db.query(
            AudioEvent.visitor_id,
            func.min(AudioEvent.ip_address).label("ip_address"),
            func.min(AudioEvent.created_at).label("first_seen"),
            func.max(AudioEvent.created_at).label("last_seen"),
            func.count(case((AudioEvent.action == "generate", 1))).label("tts_count"),
            func.count(case((AudioEvent.action == "transcribe", 1))).label("stt_count"),
            func.count(case((AudioEvent.action == "play", 1))).label("play_count"),
            func.count(case((AudioEvent.action == "download", 1))).label("download_count"),
            func.sum(AudioEvent.text_length).label("total_chars"),
            func.sum(AudioEvent.audio_duration).label("total_duration"),
            func.array_agg(func.distinct(AudioEvent.voice_name)).label("top_voices"),
            func.array_agg(func.distinct(AudioEvent.language)).label("languages")
        ).filter(AudioEvent.user_id.is_(None), AudioEvent.visitor_id.isnot(None), *filters)\
        .group_by(AudioEvent.visitor_id)\
        .order_by(func.max(AudioEvent.created_at).desc())\
        .offset(offset if user_type == "guest" else 0)\
        .limit(limit if user_type == "guest" else limit)\
        .all()
        
        for g in guests_query:
            results.append({
                "user_type": "guest",
                "user_id": None,
                "user_email": None,
                "user_name": None,
                "visitor_id": g.visitor_id,
                "ip_address": str(g.ip_address) if g.ip_address else None,
                "first_seen": g.first_seen.isoformat() if g.first_seen else None,
                "last_seen": g.last_seen.isoformat() if g.last_seen else None,
                "tts_count": g.tts_count or 0,
                "stt_count": g.stt_count or 0,
                "play_count": g.play_count or 0,
                "download_count": g.download_count or 0,
                "total_characters": int(g.total_chars or 0),
                "total_minutes": round((g.total_duration or 0) / 60, 2),
                "top_voices": [v for v in (g.top_voices or []) if v],
                "languages": [l for l in (g.languages or []) if l]
            })
    
    return {
        "total": len(results),
        "items": results
    }


@router.get("/audio/timeline/{identifier}")
def get_audio_user_timeline(
    identifier: str,
    user_type: str = Query(..., regex="^(authenticated|guest)$"),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Get detailed timeline for a specific user or guest."""
    
    query = db.query(AudioEvent)
    
    if user_type == "authenticated":
        query = query.filter(AudioEvent.user_id == int(identifier))
        # Get user details
        user = db.query(User).filter(User.id == int(identifier)).first()
        user_info = {
            "user_id": user.id if user else None,
            "email": user.email if user else None,
            "username": user.username if user else None
        } if user else None
    else:
        query = query.filter(AudioEvent.visitor_id == identifier)
        user_info = {
            "visitor_id": identifier,
            "ip_address": db.query(AudioEvent.ip_address).filter(AudioEvent.visitor_id == identifier).first()
        }
    
    total = query.count()
    events = query.order_by(AudioEvent.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "user_info": user_info,
        "total_events": total,
        "events": [
            {
                "id": e.id,
                "action": e.action,
                "status": e.status,
                "voice_name": e.voice_name,
                "language": e.language,
                "text_length": e.text_length,
                "input_text": e.input_text,
                "audio_duration": e.audio_duration,
                "file_size": e.file_size,
                "processing_time_ms": e.processing_time_ms,
                "error_message": e.error_message,
                "generation_id": e.generation_id,
                "transcription_id": e.transcription_id,
                "browser": e.browser,
                "os": e.os,
                "device": e.device,
                "created_at": e.created_at.isoformat() if e.created_at else None
            }
            for e in events
        ]
    }


@router.get("/audio/events/csv")
def export_audio_events_csv(
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    user_type: Optional[str] = Query(None, regex="^(authenticated|guest)$"),
    action: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Export audio events as CSV."""
    
    query = db.query(AudioEvent)
    
    # Apply filters
    if start_date:
        query = query.filter(AudioEvent.created_at >= start_date)
    if end_date:
        query = query.filter(AudioEvent.created_at <= end_date)
    if user_type == "authenticated":
        query = query.filter(AudioEvent.user_id.isnot(None))
    elif user_type == "guest":
        query = query.filter(AudioEvent.user_id.is_(None))
    if action:
        query = query.filter(AudioEvent.action == action)
    if status:
        query = query.filter(AudioEvent.status == status)
    
    events = query.order_by(AudioEvent.created_at.desc()).limit(10000).all()
    
    # Get user emails
    user_ids = [e.user_id for e in events if e.user_id]
    users_map = {}
    if user_ids:
        users = db.query(User.id, User.email, User.username).filter(User.id.in_(user_ids)).all()
        users_map = {u.id: {"email": u.email, "username": u.username} for u in users}
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Created At", "User Type", "User Email", "User Name", "Visitor ID", "IP Address",
        "Action", "Status", "Voice Name", "Language", "Text Length", "Audio Duration (s)",
        "File Size (bytes)", "Processing Time (ms)", "Browser", "OS", "Device", "Error Message"
    ])
    
    for e in events:
        user_info = users_map.get(e.user_id, {})
        writer.writerow([
            e.id,
            e.created_at.isoformat() if e.created_at else "",
            "Authenticated" if e.user_id else "Guest",
            user_info.get("email", "") if e.user_id else "",
            user_info.get("username", "") if e.user_id else "",
            e.visitor_id or "",
            str(e.ip_address) if e.ip_address else "",
            e.action,
            e.status,
            e.voice_name or "",
            e.language or "",
            e.text_length or "",
            e.audio_duration or "",
            e.file_size or "",
            e.processing_time_ms or "",
            e.browser or "",
            e.os or "",
            e.device or "",
            e.error_message or ""
        ])
    
    output.seek(0)
    filename = f"audio_events_{datetime.now().date()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
