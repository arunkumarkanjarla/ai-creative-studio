"""
Generation size helpers for Stable Diffusion / Realistic Vision.

Sizes must be multiples of 64. We pick the closest supported aspect
ratio so reference images (e.g. 879x920) are not stretched.
"""

from __future__ import annotations

from PIL import Image

# Best balanced sizes for this app on OpenVINO GPU
# (quality vs speed/memory on Intel iGPU/dGPU)
SUPPORTED_SIZES: tuple[tuple[int, int], ...] = (
    (512, 512),  # square / near-square refs (e.g. 879x920)
    (512, 768),  # portrait
    (768, 512),  # landscape
)

# Default when no reference is attached
DEFAULT_SIZE = (512, 768)


def pick_generation_size(
    src_width: int | None = None,
    src_height: int | None = None,
) -> tuple[int, int]:
    """
    Choose the best output size.
    With a source image, match its aspect ratio.
    Without one, use the app default portrait size.
    """
    if not src_width or not src_height or src_width <= 0 or src_height <= 0:
        return DEFAULT_SIZE

    src_ratio = src_width / src_height
    best = DEFAULT_SIZE
    best_diff = abs(best[0] / best[1] - src_ratio)

    for width, height in SUPPORTED_SIZES:
        diff = abs(width / height - src_ratio)
        if diff < best_diff:
            best = (width, height)
            best_diff = diff

    return best


def fit_image_to_size(image: Image.Image, width: int, height: int) -> Image.Image:
    """
    Center-crop to the target aspect ratio, then resize.
    Avoids stretching faces/bodies from mismatched reference dims.
    """
    image = image.convert("RGB")
    src_w, src_h = image.size
    if src_w == width and src_h == height:
        return image

    target_ratio = width / height
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        # Source is wider -> crop left/right
        new_w = int(round(src_h * target_ratio))
        left = max(0, (src_w - new_w) // 2)
        box = (left, 0, left + new_w, src_h)
    else:
        # Source is taller -> crop top/bottom
        new_h = int(round(src_w / target_ratio))
        top = max(0, (src_h - new_h) // 2)
        box = (0, top, src_w, top + new_h)

    cropped = image.crop(box)
    return cropped.resize((width, height), Image.Resampling.LANCZOS)
