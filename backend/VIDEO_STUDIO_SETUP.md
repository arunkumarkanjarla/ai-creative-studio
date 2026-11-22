# Video Studio Setup

AI Video Studio generates short preview videos on CPU with a pluggable path to a remote **LTX-2.5** GPU worker.

## Local (CPU) preview engine

### Requirements

1. **FFmpeg + ffprobe** on `PATH` (video encode, concat, subtitles, audio mix)
2. **edge-tts** (already in `requirements.txt`) — needs **internet** to call Microsoft’s neural TTS voices
3. Pillow (image frames / Ken Burns / title cards)
4. PostgreSQL for job rows (`video_projects`, `video_scenes`, `video_characters`, `video_events`)

### What it does

Per scene the Local engine:

1. Synthesizes dialogue/narration with **edge-tts** using each character’s assigned voice
2. Builds visuals from uploaded character stills (Ken Burns pan/zoom) with a light **amplitude-driven mouth motion** so the speaker appears to talk
3. Falls back to title cards when a scene has no image
4. Generates an SRT from scene text/timings and optionally burns subtitles
5. Optionally mixes a simple ffmpeg tone/pad as a music bed
6. Concatenates scenes and exports **MP4** (or WebM) at the requested orientation/resolution/FPS
7. Writes a thumbnail JPEG

Jobs run in an **in-process worker** (asyncio queue, concurrency 1). No Redis required. Set `VIDEO_JOB_BACKEND=rq` later when you wire a Redis/RQ worker — the DB row is the source of truth; stale `processing` jobs are marked failed on API startup.

### Windows laptop notes

Typical setup (i7 + Iris Xe, 16 GB RAM, no NVIDIA GPU):

- Use resolution **480p / 720p / 1080p** with the Local engine
- Keep duration in the **Short** range for snappy previews (the engine also caps very long local renders)
- Install FFmpeg (`winget install Gyan.FFmpeg` or Chocolatey) and restart the terminal
- Run uvicorn inside your venv; frontend `apiUrl` → `http://localhost:8000`

## Why LTX-2.5 / Wan 2.2 cannot run on this laptop

Diffusion video models such as **LTX-2.5** and **Wan 2.2** expect a large **NVIDIA GPU (often 32 GB+ VRAM)**, CUDA, and multi‑GB weight files. An Intel Iris Xe iGPU with 16 GB shared system RAM cannot load or run them at useful quality/speed. Attempting to force CPU inference is not practical for this product path.

## Connecting a GPU worker later

1. Provision a GPU host and follow `backend/video_worker/README.md`
2. Install your model stack there (weights are **not** downloaded by this repo)
3. On the API server set:

```bash
LTX_WORKER_URL=http://gpu-host:8100
LTX_WORKER_TOKEN=shared-secret
```

4. Restart the API — the Video Studio engine selector will show **LTX-2.5 (GPU server)** as available
5. Optional: add Wav2Lip / LatentSync on the worker after the diffusion render for higher-quality lip sync

## Auth & limits

- Video generation requires a signed-in user with `can_access_video` (admins always allowed)
- Guests receive **401**
- Character images: JPG/PNG/WebP, ≤ 10 MB each, max 6 characters
- Default create rate limit: **20 jobs / user / hour**

## Storage

Generated files live under `backend/generated_videos/` (gitignored except `.gitkeep`).
