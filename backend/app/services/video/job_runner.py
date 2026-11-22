"""
In-process video job runner (default).

Jobs are persisted as VideoProject rows. Concurrency is 1.
The runner is pluggable — swap for Redis/RQ later via VIDEO_JOB_BACKEND=rq.
"""
from __future__ import annotations

import asyncio
import os
import shutil
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Protocol

from app.db.database import SessionLocal
from app.models.video import VideoProject
from app.core.video_events import log_video_event
from app.services.video.engines.base import get_engine

BACKEND_DIR = Path(__file__).resolve().parents[3]
VIDEO_ROOT = BACKEND_DIR / "generated_videos"
OUTPUT_DIR = VIDEO_ROOT / "outputs"
THUMB_DIR = VIDEO_ROOT / "thumbnails"
WORK_DIR = VIDEO_ROOT / "work"

for _d in (OUTPUT_DIR, THUMB_DIR, WORK_DIR):
    _d.mkdir(parents=True, exist_ok=True)


class JobBackend(Protocol):
    def enqueue(self, project_id: int) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...


class InProcessJobBackend:
    """Asyncio queue processed by a dedicated daemon thread (concurrency=1)."""

    def __init__(self) -> None:
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._queue: Optional[asyncio.Queue] = None
        self._thread: Optional[threading.Thread] = None
        self._stopping = False

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stopping = False
        self._thread = threading.Thread(target=self._run_loop, name="video-job-runner", daemon=True)
        self._thread.start()
        # Wait briefly for loop readiness
        for _ in range(50):
            if self._loop and self._queue:
                break
            time.sleep(0.05)

    def stop(self) -> None:
        self._stopping = True
        if self._loop and self._queue:
            asyncio.run_coroutine_threadsafe(self._queue.put(None), self._loop)

    def enqueue(self, project_id: int) -> None:
        self.start()
        if not self._loop or not self._queue:
            raise RuntimeError("Video job runner not started")
        asyncio.run_coroutine_threadsafe(self._queue.put(project_id), self._loop)

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self._loop = loop
        self._queue = asyncio.Queue()
        loop.create_task(self._worker())
        loop.run_forever()

    async def _worker(self) -> None:
        assert self._queue is not None
        while not self._stopping:
            project_id = await self._queue.get()
            if project_id is None:
                break
            try:
                await process_project(project_id)
            except Exception as exc:
                print(f"[video-job-runner] Unhandled error for project {project_id}: {exc}")
            finally:
                self._queue.task_done()


_backend: Optional[InProcessJobBackend] = None


def get_job_backend() -> InProcessJobBackend:
    global _backend
    if _backend is None:
        backend_name = (os.getenv("VIDEO_JOB_BACKEND") or "inprocess").lower()
        if backend_name in ("rq", "redis"):
            # Placeholder: fall back to in-process until Redis worker is wired.
            print("[video-job-runner] VIDEO_JOB_BACKEND=rq requested; using in-process until RQ is configured")
        _backend = InProcessJobBackend()
        _backend.start()
    return _backend


def enqueue_video_job(project_id: int) -> None:
    get_job_backend().enqueue(project_id)


def fail_stale_processing_jobs() -> int:
    """Mark jobs left in processing/queued mid-run as failed (startup recovery)."""
    db = SessionLocal()
    try:
        stale = (
            db.query(VideoProject)
            .filter(VideoProject.status.in_(["processing"]))
            .all()
        )
        count = 0
        for project in stale:
            project.status = "failed"
            project.error_message = "Interrupted by server restart"
            project.updated_at = datetime.utcnow()
            log_video_event(
                db=db,
                request=None,
                action="fail",
                user_id=project.user_id,
                project_id=project.id,
                status="failed",
                error_message=project.error_message,
                details={"reason": "stale_on_startup"},
            )
            count += 1
        db.commit()
        return count
    finally:
        db.close()


async def process_project(project_id: int) -> None:
    db = SessionLocal()
    work_dir = WORK_DIR / f"project_{project_id}"
    try:
        project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
        if not project:
            return
        if project.status not in ("queued", "processing"):
            return

        project.status = "processing"
        project.progress = 1
        project.processing_started_at = datetime.utcnow()
        project.updated_at = datetime.utcnow()
        db.commit()

        log_video_event(
            db=db,
            request=None,
            action="start",
            user_id=project.user_id,
            project_id=project.id,
            details={"engine": project.engine},
        )

        # Re-load with relationships
        db.refresh(project)
        _ = project.scenes
        _ = project.characters

        engine = get_engine(project.engine if project.engine != "ltx-2.5" else "ltx2")

        def on_progress(pct: int, message: str) -> None:
            session = SessionLocal()
            try:
                row = session.query(VideoProject).filter(VideoProject.id == project_id).first()
                if not row:
                    return
                row.progress = max(0, min(99, int(pct)))
                row.updated_at = datetime.utcnow()
                session.commit()
                if pct in (10, 25, 50, 75, 90) or pct >= 99:
                    log_video_event(
                        db=session,
                        request=None,
                        action="progress",
                        user_id=row.user_id,
                        project_id=row.id,
                        details={"progress": pct, "message": message},
                    )
            finally:
                session.close()

        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
        work_dir.mkdir(parents=True, exist_ok=True)

        started = time.time()
        result = await engine.generate(project, work_dir, progress=on_progress)
        elapsed = time.time() - started

        # Persist outputs into stable directories
        out_name = f"video_{project_id}_{int(time.time())}{result.output_path.suffix}"
        thumb_name = f"thumb_{project_id}_{int(time.time())}.jpg"
        final_out = OUTPUT_DIR / out_name
        final_thumb = THUMB_DIR / thumb_name
        shutil.copy2(result.output_path, final_out)
        if result.thumbnail_path.exists() and result.thumbnail_path.stat().st_size > 0:
            shutil.copy2(result.thumbnail_path, final_thumb)
        else:
            final_thumb = final_out  # fallback

        project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
        if not project:
            return
        project.status = "completed"
        project.progress = 100
        project.output_path = str(final_out)
        project.thumbnail_path = str(final_thumb)
        project.file_size_bytes = result.file_size_bytes
        project.duration_seconds = result.duration_seconds
        project.generation_time_seconds = elapsed
        project.completed_at = datetime.utcnow()
        project.updated_at = datetime.utcnow()
        project.error_message = None
        db.commit()

        log_video_event(
            db=db,
            request=None,
            action="complete",
            user_id=project.user_id,
            project_id=project.id,
            duration_seconds=result.duration_seconds,
            processing_time_ms=int(elapsed * 1000),
            details={
                "file_size": result.file_size_bytes,
                "engine": project.engine,
            },
        )
    except Exception as exc:
        db.rollback()
        project = db.query(VideoProject).filter(VideoProject.id == project_id).first()
        if project:
            project.status = "failed"
            project.error_message = str(exc)[:1000]
            project.updated_at = datetime.utcnow()
            db.commit()
            log_video_event(
                db=db,
                request=None,
                action="fail",
                user_id=project.user_id,
                project_id=project.id,
                status="failed",
                error_message=str(exc),
            )
        print(f"[video-job-runner] Project {project_id} failed: {exc}")
    finally:
        db.close()
        # Keep work dir for debugging short-lived; prune large frames already removed
        # Optional cleanup:
        # shutil.rmtree(work_dir, ignore_errors=True)
