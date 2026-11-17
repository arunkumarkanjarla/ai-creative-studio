"""
Lazy image model loader.

Uses Realistic Vision V6 OpenVINO when available.
Falls back to Stable Diffusion 1.5 OpenVINO.

Pipelines are reshaped to the requested size (multiples of 64).
"""

from pathlib import Path
import threading

from app.services.ai.image_sizes import DEFAULT_SIZE

BASE_DIR = Path(__file__).resolve().parents[3]

REALISTIC_VISION_DIR = BASE_DIR / "models" / "realistic-vision-v6-openvino"
SD15_DIR = BASE_DIR / "models" / "stable-diffusion-v1-5-openvino"
SD15_MODEL_ID = "stable-diffusion-v1-5/stable-diffusion-v1-5"

_image_pipe = None
_img2img_pipe = None
_image_model_name = None
_txt_size = DEFAULT_SIZE  # width, height
_img2img_size = DEFAULT_SIZE
_image_lock = threading.Lock()


def get_image_model_name() -> str:
    return _image_model_name or "not-loaded"


def get_image_size() -> tuple[int, int]:
    """Return last compiled size (img2img preferred if loaded)."""
    if _img2img_pipe is not None:
        return _img2img_size
    return _txt_size


def _model_dir_and_name() -> tuple[Path | str, str]:
    use_rv = (REALISTIC_VISION_DIR / "model_index.json").exists()
    if use_rv:
        return REALISTIC_VISION_DIR, "realistic-vision-v6-openvino"
    if (SD15_DIR / "model_index.json").exists():
        return SD15_DIR, "stable-diffusion-v1-5-openvino"
    return SD15_MODEL_ID, "stable-diffusion-v1-5-openvino"


def _disable_safety(pipe) -> None:
    pipe.safety_checker = None
    if hasattr(pipe, "feature_extractor"):
        pipe.feature_extractor = None
    if hasattr(pipe, "requires_safety_checker"):
        pipe.requires_safety_checker = False


def _set_scheduler(pipe) -> None:
    from diffusers import DPMSolverMultistepScheduler

    pipe.scheduler = DPMSolverMultistepScheduler.from_config(
        pipe.scheduler.config
    )


def _reshape_pipe(pipe, width: int, height: int):
    print(f"Compiling image model ({width}x{height})...")
    pipe.reshape(1, height, width, 1)
    pipe.compile()
    return pipe


def get_image_pipeline(width: int | None = None, height: int | None = None):
    """Return text-to-image pipeline reshaped to the requested size."""
    global _image_pipe, _image_model_name, _txt_size

    target_w, target_h = width or DEFAULT_SIZE[0], height or DEFAULT_SIZE[1]

    with _image_lock:
        if _image_pipe is None:
            from optimum.intel import OVStableDiffusionPipeline

            model_path, model_name = _model_dir_and_name()
            export = isinstance(model_path, str)

            print(f"Loading text-to-image from: {model_path}")
            kwargs = {"device": "GPU", "compile": False}
            if export:
                kwargs["export"] = True

            pipe = OVStableDiffusionPipeline.from_pretrained(
                str(model_path),
                **kwargs,
            )

            if export:
                SD15_DIR.mkdir(parents=True, exist_ok=True)
                pipe.save_pretrained(str(SD15_DIR))

            _disable_safety(pipe)
            _set_scheduler(pipe)
            pipe = _reshape_pipe(pipe, target_w, target_h)
            _image_pipe = pipe
            _image_model_name = model_name
            _txt_size = (target_w, target_h)
            print(f"Image model ready: {model_name} @ {target_w}x{target_h}")
            return _image_pipe

        if _txt_size != (target_w, target_h):
            _image_pipe = _reshape_pipe(_image_pipe, target_w, target_h)
            _txt_size = (target_w, target_h)

        return _image_pipe


def get_img2img_pipeline(width: int | None = None, height: int | None = None):
    """Return img2img pipeline reshaped to the requested size."""
    global _img2img_pipe, _image_model_name, _img2img_size

    target_w, target_h = width or DEFAULT_SIZE[0], height or DEFAULT_SIZE[1]

    with _image_lock:
        if _img2img_pipe is None:
            from optimum.intel import OVStableDiffusionImg2ImgPipeline

            model_path, model_name = _model_dir_and_name()
            if isinstance(model_path, str):
                model_path = SD15_DIR

            print(f"Loading img2img from: {model_path}")
            pipe = OVStableDiffusionImg2ImgPipeline.from_pretrained(
                str(model_path),
                device="GPU",
                compile=False,
            )
            _disable_safety(pipe)
            _set_scheduler(pipe)
            pipe = _reshape_pipe(pipe, target_w, target_h)
            _img2img_pipe = pipe
            _image_model_name = model_name
            _img2img_size = (target_w, target_h)
            print(f"Img2img model ready: {model_name} @ {target_w}x{target_h}")
            return _img2img_pipe

        if _img2img_size != (target_w, target_h):
            _img2img_pipe = _reshape_pipe(_img2img_pipe, target_w, target_h)
            _img2img_size = (target_w, target_h)

        return _img2img_pipe
