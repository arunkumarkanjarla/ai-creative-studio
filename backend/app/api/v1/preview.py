import json
from pathlib import Path
from typing import Literal
import time

from fastapi import APIRouter, Query, Request, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.core.analytics import track_usage_event, get_client_ip
from app.api.v1.dependencies import get_optional_user

router = APIRouter(prefix="/preview", tags=["Preview"])

BACKEND_DIR = Path(__file__).resolve().parents[3]
PREVIEW_DIR = BACKEND_DIR / "preview_images"
MANIFEST_PATH = PREVIEW_DIR / "manifest.json"

# Load manifest once at startup
_manifest = None


def get_manifest():
    global _manifest
    if _manifest is None and MANIFEST_PATH.exists():
        _manifest = json.loads(MANIFEST_PATH.read_text())
    return _manifest


@router.get("/sample")
def get_preview_sample(
    request: Request,
    style: str = Query(default="realistic"),
    scene: str = Query(default="beach"),
    photo_type: str = Query(default="album"),
    db: Session = Depends(get_db),
    current_user = Depends(get_optional_user),
):
    """
    Return the URL of a sample preview image matching the selected style, scene, and photo type.
    
    Priority:
    1. Match by photo style (e.g. "Realistic", "Cinematic")
    2. Match by scene (e.g. "Beach", "Mountain")
    3. Match by photo type (e.g. "passport", "social")
    4. Fallback to "realistic.jpg"
    """
    start_time = time.time()
    
    manifest = get_manifest()
    if not manifest:
        # Track failed preview
        visitor_id = request.headers.get("X-Visitor-Id")
        forwarded_for = request.headers.get("X-Forwarded-For")
        ip = get_client_ip(request, forwarded_for)
        duration_ms = int((time.time() - start_time) * 1000)
        
        track_usage_event(
            db=db,
            visitor_id=visitor_id,
            user_id=current_user.id if current_user else None,
            ip=ip,
            studio="image",
            action="preview",
            tool="sample_preview",
            success=False,
            duration_ms=duration_ms,
        )
        return {"preview_url": None, "error": "Manifest not found"}
    
    # Normalize inputs
    style_key = style.lower().strip()
    scene_key = scene.lower().strip().replace(" ", "_")
    type_key = photo_type.lower().strip().replace(" ", "_")
    
    # Build priority list
    candidates = [
        style_key,  # e.g. "realistic", "cinematic"
        scene_key,  # e.g. "beach", "mountain"
        f"{scene_key}_scene",  # e.g. "wedding_scene"
        type_key,  # e.g. "passport", "album"
        f"{type_key}_card",  # e.g. "id_card"
    ]
    
    # Find first matching image
    images_by_key = {img["key"]: img for img in manifest.get("images", [])}
    
    result = None
    for candidate in candidates:
        if candidate in images_by_key:
            img = images_by_key[candidate]
            result = {
                "preview_url": f"/preview/{img['filename']}",
                "key": img["key"],
                "photographer": img.get("photographer"),
                "source": img.get("source"),
            }
            break
    
    # Fallback to realistic
    if not result and "realistic" in images_by_key:
        img = images_by_key["realistic"]
        result = {
            "preview_url": f"/preview/{img['filename']}",
            "key": "realistic",
            "photographer": img.get("photographer"),
            "source": img.get("source"),
        }
    
    # Track usage event
    visitor_id = request.headers.get("X-Visitor-Id")
    forwarded_for = request.headers.get("X-Forwarded-For")
    ip = get_client_ip(request, forwarded_for)
    duration_ms = int((time.time() - start_time) * 1000)
    
    track_usage_event(
        db=db,
        visitor_id=visitor_id,
        user_id=current_user.id if current_user else None,
        ip=ip,
        studio="image",
        action="preview",
        tool="sample_preview",
        success=result is not None,
        duration_ms=duration_ms,
    )
    
    if result:
        return result
    
    return {"preview_url": None, "error": "No preview images available"}


@router.get("/manifest")
def get_preview_manifest():
    """Return the full manifest of available preview images."""
    manifest = get_manifest()
    if not manifest:
        return {"error": "Manifest not found"}
    return manifest
