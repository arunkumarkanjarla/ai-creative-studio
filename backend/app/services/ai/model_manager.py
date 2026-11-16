"""
Lazy image model loader.

Uses Realistic Vision V6 OpenVINO when available.
Falls back to Stable Diffusion 1.5 OpenVINO.

Model loads only on the first generate request, then stays in memory.
"""

from pathlib import Path
import threading

BASE_DIR = Path(__file__).resolve().parents[3]

REALISTIC_VISION_DIR = BASE_DIR / "models" / "realistic-vision-v6-openvino"
SD15_DIR = BASE_DIR / "models" / "stable-diffusion-v1-5-openvino"
SD15_MODEL_ID = "stable-diffusion-v1-5/stable-diffusion-v1-5"

_image_pipe = None
_image_model_name = None
_image_lock = threading.Lock()


def get_image_model_name() -> str:
    return _image_model_name or "not-loaded"


def get_image_pipeline():
    """Return cached image pipeline. Load once if needed."""
    global _image_pipe, _image_model_name

    if _image_pipe is not None:
        return _image_pipe

    with _image_lock:
        if _image_pipe is not None:
            return _image_pipe

        from optimum.intel import OVStableDiffusionPipeline
        from diffusers import DPMSolverMultistepScheduler

        use_rv = (REALISTIC_VISION_DIR / "model_index.json").exists()

        if use_rv:
            print(f"Loading Realistic Vision from: {REALISTIC_VISION_DIR}")
            pipe = OVStableDiffusionPipeline.from_pretrained(
                str(REALISTIC_VISION_DIR),
                device="GPU",
                compile=False,
            )
            model_name = "realistic-vision-v6-openvino"
            height, width = 768, 512
        elif (SD15_DIR / "model_index.json").exists():
            print(f"Loading Stable Diffusion 1.5 from: {SD15_DIR}")
            pipe = OVStableDiffusionPipeline.from_pretrained(
                str(SD15_DIR),
                device="GPU",
                compile=False,
            )
            model_name = "stable-diffusion-v1-5-openvino"
            height, width = 512, 512
        else:
            print("No local model found. Downloading SD 1.5 OpenVINO...")
            pipe = OVStableDiffusionPipeline.from_pretrained(
                SD15_MODEL_ID,
                export=True,
                device="GPU",
                compile=False,
            )
            SD15_DIR.mkdir(parents=True, exist_ok=True)
            pipe.save_pretrained(str(SD15_DIR))
            model_name = "stable-diffusion-v1-5-openvino"
            height, width = 512, 512

        # Avoid black images from false NSFW detections
        pipe.safety_checker = None
        if hasattr(pipe, "feature_extractor"):
            pipe.feature_extractor = None
        if hasattr(pipe, "requires_safety_checker"):
            pipe.requires_safety_checker = False

        pipe.scheduler = DPMSolverMultistepScheduler.from_config(
            pipe.scheduler.config
        )

        print(f"Compiling image model ({width}x{height})...")
        pipe.reshape(1, height, width, 1)
        pipe.compile()

        _image_pipe = pipe
        _image_model_name = model_name
        print(f"Image model ready: {model_name}")
        return _image_pipe
