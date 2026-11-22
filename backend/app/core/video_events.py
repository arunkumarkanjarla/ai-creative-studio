"""
Video event logging and per-user rate limits.
"""
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.orm import Session
from user_agents import parse

from app.core.analytics import get_client_ip
from app.models.video_events import VideoEvent


def log_video_event(
    db: Session,
    request: Optional[Request],
    action: str,
    user_id: Optional[int] = None,
    project_id: Optional[int] = None,
    details: Optional[dict[str, Any]] = None,
    status: str = "success",
    error_message: Optional[str] = None,
    processing_time_ms: Optional[int] = None,
    duration_seconds: Optional[float] = None,
):
    """Log a video event. Safe to call without a Request (background jobs)."""
    try:
        ip = None
        user_agent_string = None
        browser = os_name = device = None

        if request is not None:
            forwarded_for = request.headers.get("X-Forwarded-For")
            ip = get_client_ip(request, forwarded_for)
            user_agent_string = request.headers.get("User-Agent", "")
            ua = parse(user_agent_string)
            browser = ua.browser.family if ua.browser else None
            os_name = ua.os.family if ua.os else None
            device = (
                ua.device.family
                if ua.device and ua.device.family != "Other"
                else None
            )

        event = VideoEvent(
            user_id=user_id,
            ip_address=ip,
            user_agent=user_agent_string[:500] if user_agent_string else None,
            browser=browser,
            os=os_name,
            device=device,
            action=action,
            studio="video",
            details=details,
            status=status,
            error_message=error_message[:500] if error_message else None,
            processing_time_ms=processing_time_ms,
            duration_seconds=duration_seconds,
            project_id=project_id,
        )
        db.add(event)
        db.commit()
    except Exception as exc:
        print(f"Failed to log video event: {exc}")
        try:
            db.rollback()
        except Exception:
            pass


def check_video_rate_limit(
    db: Session,
    user_id: int,
    limit_per_hour: int = 20,
) -> bool:
    """Return True if the user has exceeded the create-job rate limit."""
    hour_ago = datetime.utcnow() - timedelta(hours=1)
    count = (
        db.query(VideoEvent)
        .filter(
            VideoEvent.created_at >= hour_ago,
            VideoEvent.user_id == user_id,
            VideoEvent.action == "create",
        )
        .count()
    )
    return count >= limit_per_hour
