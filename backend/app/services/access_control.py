from datetime import datetime, timedelta, timezone
from uuid import uuid4

from fastapi import HTTPException, Request, Response
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.models.ai_access import (
    AIStudioAccessSetting,
    AIGenerationAttempt,
)
from app.models.user import User


VALID_STUDIOS = {"image", "audio", "video"}
VISITOR_COOKIE = "ai_visitor_id"


def get_visitor_id(request: Request, response: Response) -> str:
    visitor_id = request.cookies.get(VISITOR_COOKIE)

    if not visitor_id:
        visitor_id = str(uuid4())

        response.set_cookie(
            key=VISITOR_COOKIE,
            value=visitor_id,
            max_age=60 * 60 * 24 * 365,
            httponly=True,
            secure=request.url.scheme == "https",
            samesite="lax",
            path="/",
        )

    return visitor_id


def get_client_ip(request: Request) -> str | None:
    # Use the connection address. Do not trust arbitrary X-Forwarded-For
    # values supplied directly by a client.
    return request.client.host if request.client else None


def get_period_start(period: str) -> datetime | None:
    now = datetime.now(timezone.utc)

    if period == "day":
        return now - timedelta(days=1)

    if period == "week":
        return now - timedelta(days=7)

    if period == "month":
        return now - timedelta(days=30)

    if period == "lifetime":
        return None

    raise HTTPException(status_code=500, detail="Invalid usage period.")


def reserve_generation(
    db: Session,
    request: Request,
    response: Response,
    studio: str,
    prompt: str,
    current_user: User | None = None,
) -> AIGenerationAttempt:
    if studio not in VALID_STUDIOS:
        raise HTTPException(status_code=400, detail="Invalid AI studio.")

    setting = db.scalar(
        select(AIStudioAccessSetting)
        .where(AIStudioAccessSetting.studio == studio)
    )

    if setting is None:
        raise HTTPException(
            status_code=503,
            detail="AI studio settings are not configured.",
        )

    visitor_id = None
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("user-agent")

    # Guests use an anonymous cookie. Authenticated users use their account.
    if current_user is None:
        if not setting.guest_access_enabled:
            raise HTTPException(
                status_code=403,
                detail="Guest access is disabled. Please log in.",
            )

        visitor_id = get_visitor_id(request, response)

        lock_key = f"guest:{visitor_id}:{studio}"
        limit = setting.guest_generation_limit
        period = setting.guest_limit_period

    else:
        if not current_user.is_active:
            raise HTTPException(status_code=403, detail="Account is inactive.")

        if current_user.role != "systemadministrator":
            permission = getattr(current_user, f"can_access_{studio}", False)
            if not permission:
                raise HTTPException(
                    status_code=403,
                    detail=f"You do not have access to the {studio} studio.",
                )

        if current_user.role == "systemadministrator":
            limit = None
        elif setting.authenticated_limit_enabled:
            limit = setting.authenticated_generation_limit
        else:
            limit = None

        period = "lifetime"
        lock_key = f"user:{current_user.id}:{studio}"

    # Serialize simultaneous attempts for the same user/visitor and studio.
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
        {"key": lock_key},
    )

    if limit is not None:
        if limit <= 0:
            raise HTTPException(
                status_code=403,
                detail="Your generation allowance is currently zero.",
            )

        period_start = get_period_start(period)

        count_query = select(func.count(AIGenerationAttempt.id)).where(
            AIGenerationAttempt.studio == studio,
            AIGenerationAttempt.status.in_(["started", "completed", "failed"]),
        )

        if current_user is None:
            count_query = count_query.where(
                AIGenerationAttempt.visitor_id == visitor_id
            )
        else:
            count_query = count_query.where(
                AIGenerationAttempt.user_id == current_user.id
            )

        if period_start:
            count_query = count_query.where(
                AIGenerationAttempt.created_at >= period_start
            )

        used = db.scalar(count_query) or 0

        if used >= limit:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "Generation limit reached.",
                    "studio": studio,
                    "limit": limit,
                    "used": used,
                    "login_required": current_user is None,
                },
            )

    attempt = AIGenerationAttempt(
        user_id=current_user.id if current_user else None,
        visitor_id=visitor_id,
        studio=studio,
        ip_address=ip_address,
        user_agent=user_agent,
        prompt=prompt,
        status="started",
    )

    try:
        db.add(attempt)
        db.commit()
        db.refresh(attempt)
        return attempt
    except Exception:
        db.rollback()
        raise