"""
Text-to-image generation helper.

Builds a CLIP-safe prompt, runs Realistic Vision (or SD1.5),
and saves PNG files into backend/generated_images/.
"""

from pathlib import Path
import time
import threading

from app.services.ai.model_manager import get_image_pipeline, get_image_model_name
from app.services.ai.prompt_builder import build_prompts

BASE_DIR = Path(__file__).resolve().parents[3]
OUTPUT_DIR = BASE_DIR / "generated_images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

_generate_lock = threading.Lock()


def generate_image_file(
    user_text: str,
    prompt_id: str | None = None,
    negative_prompt: str | None = None,
    width: int = 512,
    height: int = 768,
    steps: int = 50,
) -> dict:
    """
    Generate one image from user text + optional saved style pack.
    """
    final_prompt, built_negative, used_prompt_id = build_prompts(
        user_text=user_text,
        prompt_id=prompt_id,
    )

    if negative_prompt:
        # Allow caller override, still keep it short via builder path
        final_negative = negative_prompt
    else:
        final_negative = built_negative

    with _generate_lock:
        pipe = get_image_pipeline()
        model_name = get_image_model_name()

        # Match compiled shape for Realistic Vision portraits
        if "realistic-vision" in model_name:
            height, width = 768, 512
            steps = max(steps, 50)
        else:
            height, width = 512, 512

        start = time.time()

        result = pipe(
            prompt=final_prompt,
            negative_prompt=final_negative,
            height=height,
            width=width,
            num_inference_steps=steps,
            guidance_scale=7.0,
            num_images_per_prompt=1,
        )

        image = result.images[0]
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

        return {
            "file_name": file_name,
            "file_path": str(file_path),
            "width": width,
            "height": height,
            "format": "png",
            "seconds": seconds,
            "model_name": model_name,
            "final_prompt": final_prompt,
            "negative_prompt": final_negative,
            "prompt_id": used_prompt_id,
        }
