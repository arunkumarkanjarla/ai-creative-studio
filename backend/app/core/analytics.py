"""
Analytics tracking utilities.
Captures usage without failing requests.
"""
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from user_agents import parse

from app.models.analytics import VisitorSession, LoginSession, UsageEvent


def parse_user_agent(user_agent: str) -> dict:
    """Parse user agent string into browser, OS, device type."""
    try:
        ua = parse(user_agent)
        return {
            "browser": f"{ua.browser.family} {ua.browser.version_string}" if ua.browser.family else None,
            "os": f"{ua.os.family} {ua.os.version_string}" if ua.os.family else None,
            "device_type": "mobile" if ua.is_mobile else ("tablet" if ua.is_tablet else "desktop"),
        }
    except Exception:
        return {"browser": None, "os": None, "device_type": "desktop"}


def get_client_ip(request, forwarded_header: Optional[str] = None) -> str:
    """Extract client IP from request, respecting X-Forwarded-For."""
    if forwarded_header and "," in forwarded_header:
        return forwarded_header.split(",")[0].strip()
    if forwarded_header:
        return forwarded_header.strip()
    return request.client.host if request.client else "unknown"


def track_page_visit(
    db: Session,
    visitor_id: str,
    user_id: Optional[int],
    ip: str,
    user_agent: Optional[str],
    path: str,
    studio: Optional[str] = None,
) -> None:
    """Track a page visit. Never raises exceptions."""
    try:
        ua_info = parse_user_agent(user_agent) if user_agent else {}
        
        visit = VisitorSession(
            visitor_id=visitor_id,
            user_id=user_id,
            ip_address=ip,
            user_agent=user_agent,
            browser=ua_info.get("browser"),
            os=ua_info.get("os"),
            device_type=ua_info.get("device_type"),
            path=path,
            studio=studio,
        )
        db.add(visit)
        db.commit()
    except Exception as e:
        print(f"[Analytics] Failed to track page visit: {e}")
        db.rollback()


def track_login_attempt(
    db: Session,
    username: Optional[str],
    user_id: Optional[int],
    ip: str,
    user_agent: Optional[str],
    status: str,
    failure_reason: Optional[str] = None,
) -> None:
    """Track a login attempt. Never raises exceptions."""
    try:
        ua_info = parse_user_agent(user_agent) if user_agent else {}
        
        session = LoginSession(
            user_id=user_id,
            username_attempted=username,
            ip_address=ip,
            user_agent=user_agent,
            browser=ua_info.get("browser"),
            os=ua_info.get("os"),
            device_type=ua_info.get("device_type"),
            login_at=datetime.utcnow(),
            status=status,
            failure_reason=failure_reason,
        )
        db.add(session)
        db.commit()
    except Exception as e:
        print(f"[Analytics] Failed to track login: {e}")
        db.rollback()


def track_usage_event(
    db: Session,
    visitor_id: Optional[str],
    user_id: Optional[int],
    ip: str,
    studio: Optional[str],
    action: str,
    tool: Optional[str] = None,
    success: bool = True,
    duration_ms: Optional[int] = None,
) -> None:
    """Track a usage event. Never raises exceptions."""
    try:
        event = UsageEvent(
            user_id=user_id,
            visitor_id=visitor_id,
            ip_address=ip,
            studio=studio,
            action=action,
            tool=tool,
            success=success,
            duration_ms=duration_ms,
        )
        db.add(event)
        db.commit()
    except Exception as e:
        print(f"[Analytics] Failed to track usage event: {e}")
        db.rollback()
