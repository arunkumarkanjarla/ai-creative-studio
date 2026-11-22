# Video Studio Setup

AI Video Studio generates short preview videos on CPU with a pluggable path to a remote **LTX-2.5** GPU worker.

## Local (CPU) cinematic preview engine

### Requirements

1. **FFmpeg + ffprobe** on `PATH` (video encode, concat, xfade transitions, subtitles, audio mix)
2. **edge-tts** (already in `requirements.txt`) — needs **internet** to call Microsoft’s neural TTS voices
3. **Pillow + NumPy** — frame compositing, procedural backgrounds, motion
4. **rembg + onnxruntime** — CPU character background removal (cutouts cached under `generated_videos/cutout_cache/`) with edge erode/feather cleanup
5. **Noto Sans Telugu** + **Noto Sans** (OFL) bundled at `backend/app/assets/fonts/` — dialogue burned in-frame with **Pillow + raqm/HarfBuzz** (correct Telugu conjuncts) inside a semi-transparent box; ASS + string list also written for verification. Falls back to Windows **Nirmala UI** when present.
6. PostgreSQL for job rows (`video_projects`, `video_scenes`, `video_characters`, `video_events`)

### What it does

Per scene the Local cinematic engine:

1. Synthesizes dialogue/narration with **edge-tts** using each character’s assigned voice
2. Builds a **scene background** with priority:
   1. Optional **per-scene uploaded image** (`scene_images` multipart field)
   2. Optional text-to-image via the Image Studio pipeline when `VIDEO_GENERATE_SCENE_BG=1` (off by default — too slow on laptop CPUs)
   3. Fallback: **procedural mood gradient + bokeh** keyed to prompt words (sunset, night, beach, home, …)
3. **Cuts out** character portraits (rembg) and composites them over the background with **parallax** (background and characters move at different speeds)
4. Applies **motion presets** (slow push-in/pull-out, pan, dolly, handheld) plus keyword actions:
   - hug/embrace → characters move together
   - celebrate/happy/success → bounce + confetti
   - walk/arrive → slide-in entrance
   - sad/emotional → slow push-in + desaturate
   - night/study → lamp glow flicker
   - sea/waves → animated wave overlay
5. **Mouth motion** from the audio amplitude envelope on the **speaking character only**; listener gets a smaller reaction / two-shot layout; close-up when dialogue is loud
6. **Transitions** between scenes (crossfade, fade-to-black, slide), optional light leaks, cinematic **letterbox** for drama/movie categories
7. Optional / category-driven **background music bed** ducked under dialogue
8. Honours **target duration**: if dialogue is shorter than the scene, the shot **holds with continued motion** (not a static freeze) so a 5-scene 45 s request lands near 45 s
9. Encodes by **piping raw RGB frames into ffmpeg** (`libx264` veryfast) for CPU-friendly throughput — target roughly a **45 s 720p portrait** render in **under ~5 minutes** on a 4-core laptop CPU
10. Writes a thumbnail JPEG and reports `render_seconds` in engine metadata

Jobs run in an **in-process worker** (asyncio queue, concurrency 1). No Redis required. Set `VIDEO_JOB_BACKEND=rq` later when you wire a Redis/RQ worker — the DB row is the source of truth; stale `processing` jobs are marked failed on API startup.

### Environment knobs

| Variable | Default | Meaning |
|----------|---------|---------|
| `VIDEO_GENERATE_SCENE_BG` | `0` | Set to `1` to try Image Studio / OpenVINO backgrounds per scene (heavy on CPU) |

### Windows laptop notes

Typical setup (i7 + Iris Xe, 16 GB RAM, no NVIDIA GPU):

- Use resolution **480p / 720p / 1080p** with the Local engine
- Keep duration in the **Short / ~45–60 s** range for snappy cinematic previews
- Install FFmpeg (`winget install Gyan.FFmpeg` or Chocolatey) and restart the terminal
- Run uvicorn inside your venv; frontend `apiUrl` → `http://localhost:8000`
- First rembg run downloads the `u2net` ONNX model; later cutouts hit the disk cache

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
- Sessions persist via **refresh tokens** until explicit Logout (see `/auth/refresh`)
- Character / scene images: JPG/PNG/WebP, ≤ 10 MB each, max 6 characters
- Default create rate limit: **20 jobs / user / hour**

## Storage

Generated files live under `backend/generated_videos/` (gitignored except `.gitkeep`):

- `characters/` — uploaded portraits
- `scenes/` — optional per-scene backgrounds
- `cutout_cache/` — rembg RGBA cutouts
- `work/` — per-job temp frames/audio
- `outputs/` / `thumbnails/` — finals
