"""
LTX-2.5 GPU worker scaffold.

Does not download model weights. Plug your LTX / Wan pipeline into
`run_generation` when deploying on a GPU host.
"""
from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(title="LTX-2.5 Video Worker", version="0.1.0")

OUTPUT_DIR = Path(os.getenv("LTX_OUTPUT_DIR", "./ltx_outputs"))
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
API_TOKEN = os.getenv("LTX_API_TOKEN") or ""

_JOBS: dict[str, dict[str, Any]] = {}


class CharacterIn(BaseModel):
    name: str
    voice_id: Optional[str] = None
    image_path: Optional[str] = None


class SceneIn(BaseModel):
    index: int = 0
    prompt: Optional[str] = None
    dialogue_text: Optional[str] = None
    character_name: Optional[str] = None
    duration_seconds: Optional[float] = None


class GenerateRequest(BaseModel):
    project_id: Optional[int] = None
    prompt: str
    category: str = "custom"
    duration_seconds: float = 30
    orientation: str = "landscape"
    resolution: str = "1080p"
    fps: int = 24
    audio_mode: str = "dialogue"
    subtitles: bool = True
    output_format: str = "mp4"
    scenes: list[SceneIn] = Field(default_factory=list)
    characters: list[CharacterIn] = Field(default_factory=list)
    callback_url: Optional[str] = None


def _check_auth(authorization: Optional[str]) -> None:
    if not API_TOKEN:
        return
    if not authorization or authorization != f"Bearer {API_TOKEN}":
        raise HTTPException(status_code=401, detail="Unauthorized")


@app.get("/health")
def health():
    cuda = False
    try:
        import torch  # type: ignore

        cuda = bool(torch.cuda.is_available())
    except Exception:
        cuda = False
    return {"status": "ok", "cuda": cuda, "model_loaded": False}


@app.post("/v1/generate", status_code=202)
def generate(req: GenerateRequest, authorization: Optional[str] = Header(None)):
    _check_auth(authorization)
    job_id = f"ltx-{uuid.uuid4().hex[:12]}"
    _JOBS[job_id] = {
        "status": "failed",
        "progress": 0,
        "download_url": None,
        "thumbnail_url": None,
        "error": (
            "Scaffold only — install LTX-2.5/Wan weights and implement "
            "run_generation() on a GPU host (32GB+ VRAM). "
            "Optional: Wav2Lip/LatentSync lip-sync after render."
        ),
        "duration_seconds": None,
        "request": req.model_dump(),
    }
    # Intentionally not running a real model. Replace with:
    # background_tasks.add_task(run_generation, job_id, req)
    raise HTTPException(
        status_code=501,
        detail=_JOBS[job_id]["error"],
    )


@app.get("/v1/jobs/{job_id}")
def job_status(job_id: str, authorization: Optional[str] = Header(None)):
    _check_auth(authorization)
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "status": job["status"],
        "progress": job["progress"],
        "download_url": job["download_url"],
        "thumbnail_url": job["thumbnail_url"],
        "error": job["error"],
        "duration_seconds": job["duration_seconds"],
    }


def run_generation(job_id: str, req: GenerateRequest) -> None:
    """Hook for real LTX-2.5 inference + optional Wav2Lip/LatentSync."""
    raise NotImplementedError("Wire your GPU pipeline here")
