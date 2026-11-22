# LTX-2.5 GPU Video Worker (scaffold)

This package is a **separate** service intended to run on a GPU machine
(typically **32 GB+ VRAM**) and expose an HTTP API consumed by the main
AI Creative Studio backend via `LTX_WORKER_URL`.

> Model weights are **not** bundled or downloaded by this scaffold.
> Install and configure LTX-2.5 / Wan 2.2 (or your chosen diffusion video
> stack) yourself on the GPU host.

## Why a separate worker?

The Local (CPU) preview engine on a laptop (e.g. Intel Iris Xe, 16 GB RAM)
cannot run LTX-2.5 or Wan 2.2. Those models need a large NVIDIA GPU.
This worker lets you keep the API server on a CPU box and offload heavy
generation to a remote GPU machine.

## Environment

Create a dedicated Python **3.12** virtualenv on the GPU host:

```bash
python3.12 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Set:

| Variable | Description |
|----------|-------------|
| `LTX_API_TOKEN` | Optional bearer token the main API sends as `LTX_WORKER_TOKEN` |
| `LTX_OUTPUT_DIR` | Where completed videos are stored |
| `CUDA_VISIBLE_DEVICES` | GPU selection |

On the main API server:

```bash
LTX_WORKER_URL=http://gpu-host:8100
LTX_WORKER_TOKEN=shared-secret
```

## HTTP contract

### `POST /v1/generate`

Request body (JSON) — see `app/services/video/engines/ltx2_engine.py` for the
full schema (`prompt`, `scenes`, `characters`, resolution, fps, etc.).

Response `202`:

```json
{"job_id": "ltx-...", "status": "queued"}
```

### `GET /v1/jobs/{job_id}`

```json
{
  "status": "queued|processing|completed|failed",
  "progress": 0,
  "download_url": "http://gpu-host:8100/files/...",
  "thumbnail_url": "http://gpu-host:8100/files/...",
  "error": null,
  "duration_seconds": 12.3
}
```

### `GET /health`

```json
{"status": "ok", "cuda": true, "model_loaded": false}
```

## Optional lip-sync step

After the base video is generated, you may optionally run a lip-sync pass
such as **Wav2Lip** or **LatentSync** using the scene dialogue audio.
That step is **not** implemented in this scaffold — wire it in after the
diffusion render if you need higher-quality mouth sync than the Local
engine's amplitude approximation.

## Run (scaffold)

```bash
uvicorn worker_app:app --host 0.0.0.0 --port 8100
```

The scaffold returns `501` for generate until you plug in real model code
in `worker_app.py`.
