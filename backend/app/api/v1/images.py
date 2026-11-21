from datetime import datetime, timezone
from math import ceil
from pathlib import Path
from typing import Literal, Optional
import threading
import time as time_module

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

from app.db.database import SessionLocal, get_db
from app.models.generated_image import GeneratedImage
from app.models.user import User
from app.models.ai_access import AIGenerationAttempt
from app.schemas.generated_image import (
    ImageGenerateResponse,
    ImageJobStartResponse,
    ImageJobStatusResponse,
    ImageHistoryItem,
    ImageHistoryResponse,
    PromptPackItem,
)
from app.api.v1.dependencies import get_optional_user, require_admin
from app.services.access_control import reserve_generation, get_visitor_id
from app.services.ai.image_service import generate_image_file
from app.services.ai.job_progress import (
    complete_job,
    fail_job,
    get_job,
    set_progress,
    start_job,
)
from app.services.ai.prompt_store import (
    create_prompt_pack,
    delete_prompt_pack,
    list_prompts,
    load_meta,
)
from app.core.analytics import track_usage_event


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


GUEST_ALLOWED_TOOLS = {"text_to_image", ""}


def _run_image_job(
    image_id: int,
    attempt_id: int,
    prompt: str,
    prompt_id: str | None,
    negative_prompt: str | None,
    width: int | None = None,
    height: int | None = None,
) -> None:
    """Background worker so the API can return progress while generating."""
    db = SessionLocal()
    start_time = time_module.time()
    try:
        start_job(image_id)
        set_progress(image_id, 2, "Preparing...")

        def on_progress(percent: int, message: str) -> None:
            set_progress(image_id, percent, message)

        result = generate_image_file(
            user_text=prompt,
            prompt_id=prompt_id,
            negative_prompt=negative_prompt,
            width=width,
            height=height,
            on_progress=on_progress,
        )

        image_row = db.get(GeneratedImage, image_id)
        attempt = db.get(AIGenerationAttempt, attempt_id)
        if not image_row:
            fail_job(image_id, "Image record not found.")
            return

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

        if attempt:
            attempt.status = "completed"
            attempt.completed_at = datetime.now(timezone.utc)
            db.add(attempt)

        db.commit()
        db.refresh(image_row)

        complete_job(
            image_id,
            {
                "id": image_row.id,
                "prompt": image_row.prompt,
                "negative_prompt": image_row.negative_prompt,
                "status": image_row.status,
                "image_url": build_image_url(image_row.image_path),
                "model_name": image_row.model_name,
                "image_width": image_row.image_width,
                "image_height": image_row.image_height,
                "generation_time_seconds": image_row.generation_time_seconds,
                "error_message": None,
                "prompt_id": result.get("prompt_id"),
                "created_at": image_row.created_at,
            },
        )
        
        # Track successful generation
        duration_ms = int((time_module.time() - start_time) * 1000)
        if attempt:
            track_usage_event(
                db=db,
                visitor_id=attempt.visitor_id,
                user_id=image_row.user_id,
                ip=attempt.ip_address,
                studio="image",
                action="generate",
                tool="text_to_image",
                success=True,
                duration_ms=duration_ms,
            )
    except Exception as error:
        try:
            image_row = db.get(GeneratedImage, image_id)
            attempt = db.get(AIGenerationAttempt, attempt_id)
            if image_row:
                image_row.status = "failed"
                image_row.error_message = str(error)
                image_row.updated_at = datetime.now(timezone.utc)
                db.add(image_row)
            if attempt:
                attempt.status = "failed"
                attempt.error_message = str(error)
                attempt.completed_at = datetime.now(timezone.utc)
                db.add(attempt)
            db.commit()
            
            # Track failed generation
            duration_ms = int((time_module.time() - start_time) * 1000)
            if attempt:
                track_usage_event(
                    db=db,
                    visitor_id=attempt.visitor_id,
                    user_id=image_row.user_id if image_row else None,
                    ip=attempt.ip_address,
                    studio="image",
                    action="generate",
                    tool="text_to_image",
                    success=False,
                    duration_ms=duration_ms,
                )
        except Exception:
            db.rollback()
        fail_job(image_id, str(error))
    finally:
        db.close()


@router.post("/generate", response_model=ImageJobStartResponse)
async def generate_image(
    request: Request,
    response: Response,
    prompt: str = Form(...),
    style_title: str = Form(""),
    prompt_id: str = Form(""),
    tool: str = Form("text_to_image"),
    width: int = Form(0),
    height: int = Form(0),
    photo_type: str = Form(""),
    photo_style: str = Form(""),
    scene: str = Form(""),
    reference: UploadFile | None = File(None),
    reference_secondary: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_user),
):
    """
    Start image generation.
    Guests may only use text_to_image.
    Logged-in users can use the full Photo Studio tool set.
    """
    prompt_text = prompt.strip()
    if len(prompt_text) < 3:
        raise HTTPException(status_code=400, detail="Prompt is required.")

    tool_name = (tool or "text_to_image").strip().lower()
    if current_user is None and tool_name not in GUEST_ALLOWED_TOOLS:
        raise HTTPException(
            status_code=401,
            detail="Sign in to use this Photo Studio feature.",
        )

    # Optional size hint from the UI (must be multiples of 64)
    out_w = width if width and width % 64 == 0 else None
    out_h = height if height and height % 64 == 0 else None

    used_prompt_id: str | None = prompt_id.strip() or None

    # Apply studio settings into the generation prompt when present
    style_bit = (photo_style or "").strip()
    scene_bit = (scene or "").strip()
    type_bit = (photo_type or "").strip().lower()
    type_hints = {
        "passport": "passport photo framing, plain backdrop, centered subject",
        "id": "ID card photo framing, neutral backdrop, head and shoulders",
        "album": "album print composition, natural portrait framing",
        "social": "social media photo composition, eye-catching framing",
        "poster": "poster composition, bold subject placement",
    }
    extras: list[str] = []
    if style_bit and style_bit.lower() not in prompt_text.lower():
        extras.append(f"{style_bit.lower()} photography")
    if scene_bit and scene_bit.lower() != "custom" and scene_bit.lower() not in prompt_text.lower():
        extras.append(f"{scene_bit.lower()} background")
    type_hint = type_hints.get(type_bit, "")
    if type_hint and type_hint.lower() not in prompt_text.lower():
        extras.append(type_hint)
    if extras:
        prompt_text = f"{prompt_text}, {', '.join(extras)}"

    _ = reference_secondary

    # If a reference file is attached, save it now with a prompt_id
    if reference is not None and reference.filename:
        content_type = (reference.content_type or "").lower()
        if not content_type.startswith("image/"):
            raise HTTPException(
                status_code=400,
                detail="Reference must be an image file.",
            )

        data = await reference.read()
        if not data:
            raise HTTPException(status_code=400, detail="Empty reference image.")
        if len(data) > 8 * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail="Reference image must be under 8 MB.",
            )

        # Auto title from prompt (no UI style-name fields)
        title = style_title.strip() or prompt_text[:60] or "generated-reference"
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
            description=f"Saved during generate: {prompt_text[:120]}",
            base_prompt=prompt_text,
            negative_prompt=None,
            image_bytes=data,
            image_ext=ext,
            created_by=created_by,
        )
        used_prompt_id = pack["prompt_id"]

    elif used_prompt_id and not load_meta(used_prompt_id):
        raise HTTPException(status_code=404, detail="Style pack not found.")

    attempt = reserve_generation(
        db=db,
        request=request,
        response=response,
        studio="image",
        prompt=prompt_text,
        current_user=current_user,
    )

    image_row = GeneratedImage(
        user_id=current_user.id if current_user else None,
        visitor_id=attempt.visitor_id,
        prompt=prompt_text,
        negative_prompt=None,
        status="processing",
        model_name="pending",
    )
    db.add(image_row)
    db.commit()
    db.refresh(image_row)

    start_job(image_row.id)
    set_progress(image_row.id, 1, "Queued...")

    worker = threading.Thread(
        target=_run_image_job,
        args=(
            image_row.id,
            attempt.id,
            prompt_text,
            used_prompt_id,
            None,
            out_w,
            out_h,
        ),
        daemon=True,
    )
    worker.start()

    return ImageJobStartResponse(
        job_id=image_row.id,
        status="processing",
        progress=1,
        message="Queued...",
    )


@router.get("/jobs/{job_id}", response_model=ImageJobStatusResponse)
def get_generate_job_status(job_id: int):
    """Poll generation progress (0-100%)."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    result = None
    if job.get("result"):
        result = ImageGenerateResponse(**job["result"])

    return ImageJobStatusResponse(
        job_id=job_id,
        status=job["status"],
        progress=job["progress"],
        message=job.get("message") or "",
        image_url=job.get("image_url"),
        error=job.get("error"),
        result=result,
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
    created_by: Literal["all", "guest", "user"] = Query(default="all"),
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

    if created_by == "guest":
        query = query.where(GeneratedImage.user_id.is_(None))
        count_query = count_query.where(GeneratedImage.user_id.is_(None))
    elif created_by == "user":
        query = query.where(GeneratedImage.user_id.is_not(None))
        count_query = count_query.where(GeneratedImage.user_id.is_not(None))

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
