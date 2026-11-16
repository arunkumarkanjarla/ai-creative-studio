"""
Store reference images and prompt packs on disk.

Folder layout:
  backend/reference_images/
    catalog.json
    <prompt_id>/
      meta.json
      reference.jpg   (or .png)
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import json
import re
import shutil
import uuid

BASE_DIR = Path(__file__).resolve().parents[3]
REFERENCE_ROOT = BASE_DIR / "reference_images"
CATALOG_FILE = REFERENCE_ROOT / "catalog.json"

REFERENCE_ROOT.mkdir(parents=True, exist_ok=True)


DEFAULT_NEGATIVE = (
    "nsfw, nude, deformed, bad anatomy, extra fingers, "
    "plastic skin, doll face, blurry, low quality, "
    "cgi, anime, cartoon, painting, watermark, text"
)

# Only used when creating a new uploaded style with empty base_prompt
DEFAULT_STYLE_PROMPT = (
    "RAW photo, natural lighting, high detail, sharp focus, 85mm"
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_catalog() -> list[str]:
    if not CATALOG_FILE.exists():
        return []
    try:
        data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        return list(data.get("prompt_ids", []))
    except Exception:
        return []


def _write_catalog(prompt_ids: list[str]) -> None:
    CATALOG_FILE.write_text(
        json.dumps({"prompt_ids": prompt_ids}, indent=2),
        encoding="utf-8",
    )


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return cleaned[:40] or "style"


def make_prompt_id(title: str) -> str:
    return f"{_slug(title)}-{uuid.uuid4().hex[:6]}"


def prompt_dir(prompt_id: str) -> Path:
    return REFERENCE_ROOT / prompt_id


def load_meta(prompt_id: str) -> dict | None:
    meta_path = prompt_dir(prompt_id) / "meta.json"
    if not meta_path.exists():
        return None
    return json.loads(meta_path.read_text(encoding="utf-8"))


def save_meta(prompt_id: str, meta: dict) -> dict:
    folder = prompt_dir(prompt_id)
    folder.mkdir(parents=True, exist_ok=True)
    meta_path = folder / "meta.json"
    meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    ids = _read_catalog()
    if prompt_id not in ids:
        ids.insert(0, prompt_id)
        _write_catalog(ids)

    return meta


def find_reference_file(prompt_id: str) -> Path | None:
    folder = prompt_dir(prompt_id)
    if not folder.exists():
        return None
    for name in ("reference.jpg", "reference.jpeg", "reference.png", "reference.webp"):
        path = folder / name
        if path.exists():
            return path
    # fallback: first image file
    for path in folder.iterdir():
        if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".webp"}:
            return path
    return None


def list_prompts() -> list[dict]:
    items: list[dict] = []
    for prompt_id in _read_catalog():
        meta = load_meta(prompt_id)
        if not meta:
            continue
        ref = find_reference_file(prompt_id)
        items.append(
            {
                **meta,
                "has_reference": ref is not None,
                "reference_url": (
                    f"/reference/{prompt_id}/{ref.name}" if ref else None
                ),
            }
        )
    return items


def create_prompt_pack(
    title: str,
    description: str,
    base_prompt: str | None,
    negative_prompt: str | None,
    image_bytes: bytes,
    image_ext: str,
    created_by: str,
) -> dict:
    prompt_id = make_prompt_id(title)
    folder = prompt_dir(prompt_id)
    folder.mkdir(parents=True, exist_ok=True)

    ext = image_ext.lower().lstrip(".")
    if ext not in {"jpg", "jpeg", "png", "webp"}:
        ext = "jpg"
    if ext == "jpeg":
        ext = "jpg"

    reference_path = folder / f"reference.{ext}"
    reference_path.write_bytes(image_bytes)

    meta = {
        "prompt_id": prompt_id,
        "title": title.strip(),
        "description": description.strip(),
        "base_prompt": (base_prompt or DEFAULT_STYLE_PROMPT).strip(),
        "negative_prompt": (negative_prompt or DEFAULT_NEGATIVE).strip(),
        "created_by": created_by,
        "created_at": _now(),
    }
    save_meta(prompt_id, meta)

    return {
        **meta,
        "has_reference": True,
        "reference_url": f"/reference/{prompt_id}/{reference_path.name}",
    }


def delete_prompt_pack(prompt_id: str) -> bool:
    """Delete one reference style pack folder and remove it from catalog."""
    safe_id = (prompt_id or "").strip()
    if (
        not safe_id
        or safe_id in {"_seed", ".", ".."}
        or "/" in safe_id
        or "\\" in safe_id
        or ".." in safe_id
    ):
        return False

    folder = prompt_dir(safe_id)
    # Resolve and ensure delete stays inside reference_images
    try:
        resolved = folder.resolve()
        root = REFERENCE_ROOT.resolve()
        if root not in resolved.parents and resolved != root:
            return False
    except Exception:
        return False

    if folder.exists() and folder.is_dir():
        shutil.rmtree(folder, ignore_errors=False)

    ids = [item for item in _read_catalog() if item != safe_id]
    _write_catalog(ids)

    # Treat as success if folder is gone even if it was already missing
    return not folder.exists()
