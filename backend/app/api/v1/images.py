from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from typing import Literal, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.generated_image import GeneratedImage
from app.models.user import User
from app.models.ai_access import AIGenerationAttempt
from app.schemas.generated_image import (
    ImageGenerateRequest,
    ImageGenerateResponse,
    ImageHistoryItem,
    ImageHistoryResponse,
    PromptPackItem,
)
from app.api.v1.dependencies import get_optional_user, require_admin
from app.services.access_control import reserve_generation, get_visitor_id
from app.services.ai.image_service import generate_image_file
from app.services.ai.prompt_store import (
    create_prompt_pack,
    delete_prompt_pack,
    list_prompts,
    load_meta,
)


router = APIRouter(prefix="/images", tags=["Text-to-Image"])

IMAGE_URL_PREFIX = "/generated"
GENERATED_DIR = Path(__file__).resolve().parents[3] / "generated_images"


def build_image_url(file_name: str | None) -> str | None:
    if not file_name:
        return None
    name = file_name.replace("\\", "/").split("/")[-1]
    return f"{IMAGE_URL_PREFIX}/{name}"


def mark_attempt(
    db: Session,
    attempt: AIGenerationAttempt,
    status: str,
    error_message: str | None = None,
) -> None:
    attempt.status = status
    attempt.error_message = error_message
    if status in ("completed", "failed"):
        attempt.completed_at = datetime.now(timezone.utc)
    db.add(attempt)
    db.commit()


@router.get("/prompts", response_model=list[PromptPackItem])
def get_prompt_packs():
    """List saved style packs. Does not recreate deleted styles."""
    return list_prompts()


@router.delete("/prompts/{prompt_id}")
def remove_prompt_pack(
    prompt_id: str,
    admin: User = Depends(require_admin),
):
    """Admin: delete one reference style pack folder permanently."""
    deleted = delete_prompt_pack(prompt_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Reference style not found.")
    return {"message": "Reference style deleted.", "prompt_id": prompt_id}


@router.delete("/{image_id}")
def remove_generated_image(
    image_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """Admin: delete one generated image from DB and disk."""
    image = db.get(GeneratedImage, image_id)
    if not image:
        raise HTTPException(status_code=404, detail="Generated image not found.")

    file_name = image.image_path
    db.delete(image)
    db.commit()

    if file_name:
        name = str(file_name).replace("\\", "/").split("/")[-1]
        file_path = GENERATED_DIR / name
        if file_path.exists() and file_path.is_file():
            file_path.unlink()

    return {"message": "Generated image deleted.", "id": image_id}


@router.post("/prompts", response_model=PromptPackItem)
async def upload_prompt_pack(
    title: str = Form(...),
    description: str = Form(""),
    base_prompt: str = Form(""),
    negative_prompt: str = Form(""),
    reference: UploadFile = File(...),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Guest / user / admin can upload a reference image.
    It is saved under reference_images/<prompt_id>/.
    """
    if not title.strip():
        raise HTTPException(status_code=400, detail="Title is required.")

    content_type = (reference.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")

    data = await reference.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty image file.")
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="Image must be under 8 MB.")

    filename = reference.filename or "reference.jpg"
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"

    created_by = "guest"
    if current_user:
        created_by = (
            "admin"
            if current_user.role == "systemadministrator"
            else f"user:{current_user.id}"
        )

    pack = create_prompt_pack(
        title=title,
        description=description,
        base_prompt=base_prompt or None,
        negative_prompt=negative_prompt or None,
        image_bytes=data,
        image_ext=ext,
        created_by=created_by,
    )
    return pack


@router.post("/generate", response_model=ImageGenerateResponse)
def generate_image(
    data: ImageGenerateRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    prompt = data.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")

    if data.prompt_id and not load_meta(data.prompt_id):
        raise HTTPException(status_code=404, detail="Style pack not found.")

    # Check guest/user limits and create an attempt row
    attempt = reserve_generation(
        db=db,
        request=request,
        response=response,
        studio="image",
        prompt=prompt,
        current_user=current_user,
    )

    visitor_id = attempt.visitor_id

    image_row = GeneratedImage(
        user_id=current_user.id if current_user else None,
        visitor_id=visitor_id,
        prompt=prompt,
        negative_prompt=data.negative_prompt,
        status="processing",
        model_name="pending",
    )
    db.add(image_row)
    db.commit()
    db.refresh(image_row)

    try:
        result = generate_image_file(
            user_text=prompt,
            prompt_id=data.prompt_id,
            negative_prompt=data.negative_prompt,
        )

        # Store the final CLIP-safe prompt that was actually used
        image_row.prompt = result["final_prompt"]
        image_row.negative_prompt = result["negative_prompt"]
        image_row.image_path = result["file_name"]
        image_row.thumbnail_path = result["file_name"]
        image_row.image_width = result["width"]
        image_row.image_height = result["height"]
        image_row.image_format = result["format"]
        image_row.generation_time_seconds = result["seconds"]
        image_row.model_name = result["model_name"]
        image_row.status = "completed"
        image_row.updated_at = datetime.now(timezone.utc)

        db.add(image_row)
        db.commit()
        db.refresh(image_row)

        mark_attempt(db, attempt, "completed")

        return ImageGenerateResponse(
            id=image_row.id,
            prompt=image_row.prompt,
            negative_prompt=image_row.negative_prompt,
            status=image_row.status,
            image_url=build_image_url(image_row.image_path),
            model_name=image_row.model_name,
            image_width=image_row.image_width,
            image_height=image_row.image_height,
            generation_time_seconds=image_row.generation_time_seconds,
            error_message=None,
            prompt_id=result.get("prompt_id"),
            created_at=image_row.created_at,
        )

    except Exception as error:
        image_row.status = "failed"
        image_row.error_message = str(error)
        image_row.updated_at = datetime.now(timezone.utc)
        db.add(image_row)
        db.commit()

        mark_attempt(db, attempt, "failed", str(error))

        raise HTTPException(
            status_code=500,
            detail=f"Image generation failed: {error}",
        )


@router.get("/history", response_model=ImageHistoryResponse)
def get_image_history(
    request: Request,
    response: Response,
    prompt: str | None = Query(default=None, max_length=2000),
    status: Literal["pending", "processing", "completed", "failed"] | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    is_admin = bool(
        current_user and current_user.role == "systemadministrator"
    )

    query = (
        select(GeneratedImage, User.name, User.email)
        .outerjoin(User, GeneratedImage.user_id == User.id)
    )
    count_query = select(func.count(GeneratedImage.id))

    if is_admin:
        pass
    elif current_user is not None:
        query = query.where(GeneratedImage.user_id == current_user.id)
        count_query = count_query.where(
            GeneratedImage.user_id == current_user.id
        )
    else:
        visitor_id = get_visitor_id(request, response)
        query = query.where(GeneratedImage.visitor_id == visitor_id)
        count_query = count_query.where(
            GeneratedImage.visitor_id == visitor_id
        )

    if prompt:
        search = f"%{prompt.strip()}%"
        query = query.where(GeneratedImage.prompt.ilike(search))
        count_query = count_query.where(GeneratedImage.prompt.ilike(search))

    if status:
        query = query.where(GeneratedImage.status == status)
        count_query = count_query.where(GeneratedImage.status == status)

    total = db.scalar(count_query) or 0

    query = (
        query.order_by(GeneratedImage.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    rows = db.execute(query).all()

    items = [
        ImageHistoryItem(
            id=image.id,
            user_id=image.user_id,
            visitor_id=image.visitor_id,
            user_name=user_name or ("Guest" if image.visitor_id else None),
            user_email=user_email,
            prompt=image.prompt,
            negative_prompt=image.negative_prompt,
            model_name=image.model_name,
            image_url=build_image_url(image.image_path),
            image_path=image.image_path,
            thumbnail_path=image.thumbnail_path,
            image_width=image.image_width,
            image_height=image.image_height,
            image_format=image.image_format,
            status=image.status,
            error_message=image.error_message,
            generation_time_seconds=image.generation_time_seconds,
            created_at=image.created_at,
            updated_at=image.updated_at,
        )
        for image, user_name, user_email in rows
    ]

    return ImageHistoryResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
        items=items,
    )


@router.get("/admin/history", response_model=ImageHistoryResponse)
def get_admin_image_history(
    prompt: str | None = Query(default=None, max_length=2000),
    status: Literal["pending", "processing", "completed", "failed"] | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    query = (
        select(GeneratedImage, User.name, User.email)
        .outerjoin(User, GeneratedImage.user_id == User.id)
    )
    count_query = select(func.count(GeneratedImage.id))

    if prompt:
        search = f"%{prompt.strip()}%"
        query = query.where(GeneratedImage.prompt.ilike(search))
        count_query = count_query.where(GeneratedImage.prompt.ilike(search))

    if status:
        query = query.where(GeneratedImage.status == status)
        count_query = count_query.where(GeneratedImage.status == status)

    total = db.scalar(count_query) or 0

    query = (
        query.order_by(GeneratedImage.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    rows = db.execute(query).all()

    items = [
        ImageHistoryItem(
            id=image.id,
            user_id=image.user_id,
            visitor_id=image.visitor_id,
            user_name=user_name or ("Guest" if not image.user_id else None),
            user_email=user_email,
            prompt=image.prompt,
            negative_prompt=image.negative_prompt,
            model_name=image.model_name,
            image_url=build_image_url(image.image_path),
            image_path=image.image_path,
            thumbnail_path=image.thumbnail_path,
            image_width=image.image_width,
            image_height=image.image_height,
            image_format=image.image_format,
            status=image.status,
            error_message=image.error_message,
            generation_time_seconds=image.generation_time_seconds,
            created_at=image.created_at,
            updated_at=image.updated_at,
        )
        for image, user_name, user_email in rows
    ]

    return ImageHistoryResponse(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=ceil(total / page_size) if total else 0,
        items=items,
    )
