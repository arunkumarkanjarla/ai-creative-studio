from sqlalchemy import func
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.ai_access import AIStudioAccessSetting
from app.schemas.ai_access import (
    StudioAccessUpdate,
    StudioAccessResponse,
)
from app.api.v1.dependencies import require_admin


router = APIRouter(prefix="/ai-access", tags=["AI Access Settings"])

DEFAULT_STUDIOS = ("image", "audio", "video")


def ensure_studio_settings(db: Session) -> None:
    """Create missing image/audio/video settings rows."""
    existing = set(
        db.scalars(select(AIStudioAccessSetting.studio)).all()
    )

    created = False
    for studio in DEFAULT_STUDIOS:
        if studio not in existing:
            db.add(AIStudioAccessSetting(studio=studio))
            created = True

    if created:
        db.commit()


@router.get(
    "/settings",
    response_model=list[StudioAccessResponse],
)
def get_all_settings(
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    ensure_studio_settings(db)

    return db.scalars(
        select(AIStudioAccessSetting).order_by(
            AIStudioAccessSetting.studio
        )
    ).all()


@router.patch(
    "/settings/{studio}",
    response_model=StudioAccessResponse,
)
def update_studio_settings(
    studio: Literal["image", "audio", "video"],
    data: StudioAccessUpdate,
    db: Session = Depends(get_db),
    admin=Depends(require_admin),
):
    setting = db.scalar(
        select(AIStudioAccessSetting)
        .where(AIStudioAccessSetting.studio == studio)
        .with_for_update()
    )

    if not setting:
        raise HTTPException(
            status_code=404,
            detail="Studio settings not found.",
        )

    updates = data.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(setting, field, value)

    setting.updated_at = func.now()

    try:
        db.commit()
        db.refresh(setting)
        return setting
    except Exception:
        db.rollback()
        raise