"""
In-memory progress for image generation jobs.
Frontend polls this while the model is running.
"""

from __future__ import annotations

import threading

_lock = threading.Lock()
_jobs: dict[int, dict] = {}


def start_job(job_id: int) -> None:
    with _lock:
        _jobs[job_id] = {
            "job_id": job_id,
            "status": "processing",
            "progress": 1,
            "message": "Starting...",
            "image_url": None,
            "error": None,
            "result": None,
        }


def set_progress(job_id: int, progress: int, message: str = "") -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            return
        job["progress"] = max(0, min(100, int(progress)))
        if message:
            job["message"] = message
        job["status"] = "processing"


def complete_job(job_id: int, result: dict) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            _jobs[job_id] = {
                "job_id": job_id,
                "status": "completed",
                "progress": 100,
                "message": "Done",
                "image_url": result.get("image_url"),
                "error": None,
                "result": result,
            }
            return
        job["status"] = "completed"
        job["progress"] = 100
        job["message"] = "Done"
        job["image_url"] = result.get("image_url")
        job["error"] = None
        job["result"] = result


def fail_job(job_id: int, error: str) -> None:
    with _lock:
        job = _jobs.get(job_id)
        if not job:
            _jobs[job_id] = {
                "job_id": job_id,
                "status": "failed",
                "progress": 100,
                "message": "Failed",
                "image_url": None,
                "error": error,
                "result": None,
            }
            return
        job["status"] = "failed"
        job["progress"] = 100
        job["message"] = "Failed"
        job["error"] = error


def get_job(job_id: int) -> dict | None:
    with _lock:
        job = _jobs.get(job_id)
        return dict(job) if job else None
