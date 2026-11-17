"""
Text-to-image and reference-guided generation.

When a reference is attached, the user prompt is interpreted:
- background-only / solid color  -> keep subject pixels, replace background
- light preserve edits           -> low-strength img2img
- larger restyles                -> stronger img2img
"""

from pathlib import Path
import time
import threading
from typing import Callable

from PIL import Image

from app.services.ai.background_mask import (
    build_background_mask_array,
    composite_background,
)
from app.services.ai.image_sizes import (
    SUPPORTED_SIZES,
    fit_image_to_size,
    pick_generation_size,
)
from app.services.ai.model_manager import (
    get_image_pipeline,
    get_img2img_pipeline,
    get_image_model_name,
)
from app.services.ai.prompt_builder import build_prompts
from app.services.ai.prompt_store import find_reference_file

BASE_DIR = Path(__file__).resolve().parents[3]
OUTPUT_DIR = BASE_DIR / "generated_images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_generate_lock = threading.Lock()


def _open_reference(prompt_id: str) -> Image.Image | None:
    ref_path = find_reference_file(prompt_id)
    if not ref_path:
        return None
    return Image.open(ref_path).convert("RGB")


def _run_pipe(pipe, kwargs, steps, report, label: str):
    def step_callback(step: int, timestep, latents):
        percent = 8 + int(((step + 1) / steps) * 84)
        report(percent, f"{label}... step {step + 1}/{steps}")

    try:
        return pipe(**kwargs, callback=step_callback, callback_steps=1)
    except TypeError:
        def on_step_end(pipeline, step_index, timestep, callback_kwargs):
            percent = 8 + int(((step_index + 1) / steps) * 84)
            report(percent, f"{label}... step {step_index + 1}/{steps}")
            return callback_kwargs

        return pipe(**kwargs, callback_on_step_end=on_step_end)


def generate_image_file(
    user_text: str,
    prompt_id: str | None = None,
    negative_prompt: str | None = None,
    width: int | None = None,
    height: int | None = None,
    steps: int = 50,
    strength: float | None = None,
    on_progress: Callable[[int, str], None] | None = None,
) -> dict:
    """
    Generate one image from user text + optional reference.
    """
    final_prompt, built_negative, used_prompt_id, edit_plan = build_prompts(
        user_text=user_text,
        prompt_id=prompt_id,
    )

    final_negative = negative_prompt or built_negative

    def report(percent: int, message: str) -> None:
        if on_progress:
            on_progress(percent, message)

    with _generate_lock:
        report(3, "Loading model...")

        init_image = None
        src_w = src_h = None
        if used_prompt_id:
            report(5, "Loading reference image...")
            init_image = _open_reference(used_prompt_id)
            if init_image is not None:
                src_w, src_h = init_image.size

        if width and height:
            requested = (int(width), int(height))
            if requested in SUPPORTED_SIZES:
                out_w, out_h = requested
            else:
                out_w, out_h = pick_generation_size(requested[0], requested[1])
        else:
            out_w, out_h = pick_generation_size(src_w, src_h)

        use_reference = init_image is not None
        mode = (edit_plan or {}).get("mode") if edit_plan else None
        plan_strength = (edit_plan or {}).get("strength")
        guidance = float((edit_plan or {}).get("guidance_scale") or 7.0)
        solid_color = (edit_plan or {}).get("solid_color") if edit_plan else None

        if use_reference:
            init_image = fit_image_to_size(init_image, out_w, out_h)

        # Fast accurate path: solid background color keeps the person 1:1
        if use_reference and mode == "background" and solid_color is not None:
            report(20, "Replacing background color...")
            alpha = build_background_mask_array(init_image)
            report(70, "Compositing subject...")
            image = composite_background(init_image, tuple(solid_color), alpha)
            report(94, "Saving image...")
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            file_name = f"generated_image_{timestamp}.png"
            file_path = OUTPUT_DIR / file_name
            image.save(file_path)
            report(100, "Done")
            return {
                "file_name": file_name,
                "file_path": str(file_path),
                "width": out_w,
                "height": out_h,
                "format": "png",
                "seconds": 0.0,
                "model_name": "reference-composite",
                "final_prompt": final_prompt,
                "negative_prompt": final_negative,
                "prompt_id": used_prompt_id,
                "used_reference": True,
                "edit_mode": mode,
                "source_size": f"{src_w}x{src_h}" if src_w and src_h else None,
            }

        if use_reference:
            pipe = get_img2img_pipeline(out_w, out_h)
            steps = max(steps, 50)
            used_strength = (
                float(strength)
                if strength is not None
                else float(plan_strength or 0.4)
            )
            used_strength = max(0.22, min(used_strength, 0.75))
            report(
                8,
                f"Generating from reference ({mode or 'edit'} {out_w}x{out_h})...",
            )
        else:
            pipe = get_image_pipeline(out_w, out_h)
            model_name = get_image_model_name()
            if "realistic-vision" in model_name:
                steps = max(steps, 50)
            used_strength = None
            report(8, f"Generating image ({out_w}x{out_h})...")

        model_name = get_image_model_name()
        start = time.time()

        kwargs = {
            "prompt": final_prompt,
            "negative_prompt": final_negative,
            "num_inference_steps": steps,
            "guidance_scale": guidance,
            "num_images_per_prompt": 1,
        }

        if use_reference:
            kwargs["image"] = init_image
            kwargs["strength"] = used_strength
            label = f"Generating ({mode or 'reference'} {out_w}x{out_h})"
        else:
            kwargs["height"] = out_h
            kwargs["width"] = out_w
            label = f"Generating (text {out_w}x{out_h})"

        result = _run_pipe(pipe, kwargs, steps, report, label)
        image = result.images[0]

        # For non-solid background edits, lock the subject from the reference
        if use_reference and mode == "background":
            report(90, "Keeping subject from reference...")
            alpha = build_background_mask_array(init_image)
            image = composite_background(init_image, image, alpha)

        report(94, "Saving image...")
        extrema = image.convert("L").getextrema()
        if extrema[1] < 10:
            raise RuntimeError(
                "Generated image was blank. Try again with a different prompt."
            )

        timestamp = time.strftime("%Y%m%d_%H%M%S")
        file_name = f"generated_image_{timestamp}.png"
        file_path = OUTPUT_DIR / file_name
        image.save(file_path)

        seconds = round(time.time() - start, 2)
        report(100, "Done")

        return {
            "file_name": file_name,
            "file_path": str(file_path),
            "width": out_w,
            "height": out_h,
            "format": "png",
            "seconds": seconds,
            "model_name": model_name,
            "final_prompt": final_prompt,
            "negative_prompt": final_negative,
            "prompt_id": used_prompt_id,
            "used_reference": use_reference,
            "edit_mode": mode,
            "strength": used_strength,
            "source_size": f"{src_w}x{src_h}" if src_w and src_h else None,
        }
