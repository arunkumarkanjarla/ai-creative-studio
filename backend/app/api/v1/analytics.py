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
