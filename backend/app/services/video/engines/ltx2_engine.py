"""
LTX-2.5 remote GPU worker adapter.

Contract (HTTP JSON):

POST {LTX_WORKER_URL}/v1/generate
Authorization: Bearer {LTX_WORKER_TOKEN}  (optional)

Request:
{
  "project_id": 123,
  "prompt": "...",
  "category": "drama",
  "duration_seconds": 30,
  "orientation": "landscape",
  "resolution": "1080p",
  "fps": 24,
  "audio_mode": "dialogue",
  "subtitles": true,
  "output_format": "mp4",
  "scenes": [
    {"index": 0, "prompt": "...", "dialogue_text": "...", "character_name": "Alex", "duration_seconds": 10}
  ],
  "characters": [
    {"name": "Alex", "voice_id": "en-US-JennyNeural", "image_url": "https://..."}
  ],
  "callback_url": null
}

Response (202 Accepted):
{"job_id": "ltx-...", "status": "queued"}

GET {LTX_WORKER_URL}/v1/jobs/{job_id}
{"status": "queued|processing|completed|failed", "progress": 0-100,
 "download_url": "...", "thumbnail_url": "...", "error": null, "duration_seconds": 12.3}

When LTX_WORKER_URL is unset, this engine reports unavailable.
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from app.services.video.engines.base import (
    EngineCapabilities,
    EngineResult,
    ProgressCallback,
    VideoEngine,
)


class LTX2Engine(VideoEngine):
    engine_id = "ltx2"
    label = "LTX-2.5 (GPU server)"
    requires_gpu = True

    def __init__(self) -> None:
        self.worker_url = (os.getenv("LTX_WORKER_URL") or "").rstrip("/")
        self.worker_token = os.getenv("LTX_WORKER_TOKEN") or ""

    def capabilities(self) -> EngineCapabilities:
        if not self.worker_url:
            return EngineCapabilities(
                engine_id=self.engine_id,
                label=self.label,
                available=False,
                reason="LTX_WORKER_URL is not configured",
                requires_gpu=True,
            )
        return EngineCapabilities(
            engine_id=self.engine_id,
            label=self.label,
            available=True,
            requires_gpu=True,
        )

    async def generate(
        self,
        project: Any,
        work_dir: Path,
        progress: Optional[ProgressCallback] = None,
    ) -> EngineResult:
        caps = self.capabilities()
        if not caps.available:
            raise RuntimeError(caps.reason or "LTX-2.5 worker unavailable")

        import httpx

        def report(pct: int, message: str) -> None:
            if progress:
                progress(pct, message)

        report(5, "Submitting job to LTX-2.5 worker")

        payload = {
            "project_id": project.id,
            "prompt": project.prompt,
            "category": project.category,
            "duration_seconds": project.duration_seconds,
            "orientation": project.orientation,
            "resolution": project.resolution,
            "fps": project.fps,
            "audio_mode": project.audio_mode,
            "subtitles": project.subtitles,
            "output_format": project.output_format,
            "scenes": [
                {
                    "index": s.scene_index,
                    "prompt": s.prompt,
                    "dialogue_text": s.dialogue_text,
                    "character_name": s.character_name,
                    "duration_seconds": s.duration_seconds,
                }
                for s in (project.scenes or [])
            ],
            "characters": [
                {
                    "name": c.name,
                    "voice_id": c.voice_id,
                    "image_path": c.image_path,
                }
                for c in (project.characters or [])
            ],
        }

        headers = {"Content-Type": "application/json"}
        if self.worker_token:
            headers["Authorization"] = f"Bearer {self.worker_token}"

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{self.worker_url}/v1/generate",
                json=payload,
                headers=headers,
            )
            if resp.status_code >= 400:
                raise RuntimeError(f"LTX worker rejected job: {resp.status_code} {resp.text}")
            data = resp.json()
            job_id = data.get("job_id")
            if not job_id:
                raise RuntimeError("LTX worker response missing job_id")

            report(15, f"LTX job {job_id} queued")

            # Poll until complete
            import asyncio

            for _ in range(3600):
                await asyncio.sleep(2)
                status_resp = await client.get(
                    f"{self.worker_url}/v1/jobs/{job_id}",
                    headers=headers,
                )
                status_resp.raise_for_status()
                st = status_resp.json()
                pct = int(st.get("progress") or 0)
                report(min(95, max(15, pct)), st.get("status", "processing"))
                if st.get("status") == "completed":
                    download_url = st.get("download_url")
                    thumb_url = st.get("thumbnail_url")
                    if not download_url:
                        raise RuntimeError("LTX job completed without download_url")
                    work_dir.mkdir(parents=True, exist_ok=True)
                    out_ext = "webm" if (project.output_format or "mp4") == "webm" else "mp4"
                    output_path = work_dir / f"output.{out_ext}"
                    thumb_path = work_dir / "thumbnail.jpg"
                    async with client.stream("GET", download_url) as stream:
                        stream.raise_for_status()
                        with open(output_path, "wb") as fh:
                            async for chunk in stream.aiter_bytes():
                                fh.write(chunk)
                    if thumb_url:
                        async with client.stream("GET", thumb_url) as stream:
                            stream.raise_for_status()
                            with open(thumb_path, "wb") as fh:
                                async for chunk in stream.aiter_bytes():
                                    fh.write(chunk)
                    else:
                        thumb_path.write_bytes(b"")
                    return EngineResult(
                        output_path=output_path,
                        thumbnail_path=thumb_path,
                        duration_seconds=float(st.get("duration_seconds") or 0),
                        file_size_bytes=output_path.stat().st_size,
                        metadata={"engine": "ltx2", "remote_job_id": job_id},
                    )
                if st.get("status") == "failed":
                    raise RuntimeError(st.get("error") or "LTX job failed")

        raise RuntimeError("LTX job timed out")
