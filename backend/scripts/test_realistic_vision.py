"""
Realistic Vision V6.0 test script.

CLIP limit = 77 tokens. Keep prompts short.
Put face details first so they are never truncated.
"""

from pathlib import Path
import time

import torch
from optimum.intel import OVStableDiffusionPipeline
from diffusers import DPMSolverMultistepScheduler


BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models" / "realistic-vision-v6-openvino"
OUTPUT_DIR = BASE_DIR / "generated_images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Active look for this run
SELECTED_PROMPT = "face_reference_portrait"
SEED = 256


PROMPTS = {
    # Generic face portrait from your reference photo
    # (skin tone, eyes, brows, hair, soft smile)
    "face_reference_portrait": (
        "close-up face portrait, young indian woman, oval face, "
        "warm medium tan skin, large almond brown eyes, soft arched "
        "feminine eyebrows, straight slender nose, full lips soft smile, "
        "jet black middle part wavy hair, natural skin texture, "
        "looking at camera, plain light background, RAW photo, 85mm"
    ),
    "pink_saree_portrait": (
        "close-up upper body portrait, real indian woman, soft smile, "
        "soft arched feminine eyebrows, detailed nose lips ears eyes, "
        "pink traditional saree with matching blouse, pallu on shoulder, "
        "gold border, bindi, jhumka, long black hair, ocean background, "
        "RAW photo, sharp face, 85mm lens"
    ),
}


NEGATIVE_PROMPT = (
    "masculine face, thick straight brows, unibrow, "
    "deformed nose, bad lips, bad ears, cross eyed, "
    "plastic skin, doll face, airbrushed, makeup mask, "
    "nsfw, nude, cleavage, cgi, anime, painting, blurry, watermark"
)


def count_tokens(tokenizer, text: str) -> int:
    tokens = tokenizer(
        text,
        truncation=False,
        add_special_tokens=True,
        return_tensors=None,
    )
    return len(tokens["input_ids"])


def assert_prompt_length(tokenizer, prompt: str, negative: str) -> None:
    prompt_tokens = count_tokens(tokenizer, prompt)
    negative_tokens = count_tokens(tokenizer, negative)

    print(f"Prompt tokens: {prompt_tokens}/77")
    print(f"Negative tokens: {negative_tokens}/77")

    if prompt_tokens > 77:
        raise ValueError(
            f"Prompt is too long ({prompt_tokens} tokens). Shorten it."
        )

    if negative_tokens > 77:
        raise ValueError(
            f"Negative prompt is too long ({negative_tokens} tokens)."
        )


def main() -> None:
    if not (MODEL_DIR / "model_index.json").exists():
        raise FileNotFoundError(f"Converted model not found: {MODEL_DIR}")

    if SELECTED_PROMPT not in PROMPTS:
        raise KeyError(
            f"Unknown prompt '{SELECTED_PROMPT}'. "
            f"Choose one of: {', '.join(PROMPTS)}"
        )

    prompt = PROMPTS[SELECTED_PROMPT]

    print("Loading Realistic Vision V6.0...")
    start_time = time.time()

    pipe = OVStableDiffusionPipeline.from_pretrained(
        str(MODEL_DIR),
        device="GPU",
        compile=False,
    )

    # Disable NSFW safety filter (false positives on portraits)
    pipe.safety_checker = None
    if hasattr(pipe, "feature_extractor"):
        pipe.feature_extractor = None
    if hasattr(pipe, "requires_safety_checker"):
        pipe.requires_safety_checker = False

    pipe.scheduler = DPMSolverMultistepScheduler.from_config(
        pipe.scheduler.config
    )

    assert_prompt_length(pipe.tokenizer, prompt, NEGATIVE_PROMPT)

    print("Compiling model...")
    # App sizes: 512x512 (near-square refs), 512x768 (portrait), 768x512 (landscape)
    # Face / near-square references (e.g. 879x920) use 512x512
    width, height = 512, 512
    pipe.reshape(1, height, width, 1)
    pipe.compile()

    print(f"Selected prompt: {SELECTED_PROMPT}")
    print(f"Prompt: {prompt}")
    print(f"Size: {width}x{height}")
    print(f"Seed: {SEED}")
    print("Generating image...")

    generator = torch.Generator(device="cpu").manual_seed(SEED)

    result = pipe(
        prompt=prompt,
        negative_prompt=NEGATIVE_PROMPT,
        height=height,
        width=width,
        num_inference_steps=50,
        guidance_scale=7.0,
        generator=generator,
        num_images_per_prompt=1,
    )

    image = result.images[0]

    extrema = image.convert("L").getextrema()
    if extrema[1] < 10:
        raise RuntimeError(
            "Output image is almost black. Safety filter may still be active."
        )

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    output_file = (
        OUTPUT_DIR / f"realistic_vision_{SELECTED_PROMPT}_{timestamp}.png"
    )
    image.save(output_file)

    print("----------------------------------")
    print("REALISTIC VISION GENERATION DONE")
    print(f"Image saved: {output_file}")
    print(f"Total time: {time.time() - start_time:.2f} seconds")
    print("----------------------------------")


if __name__ == "__main__":
    main()
