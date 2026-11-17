"""
Build a soft background mask for reference edits.

White / 1.0 = background (editable)
Black / 0.0 = subject (preserve)

Prefers rembg subject cutout when available; falls back to chroma-key.
"""

from __future__ import annotations

import numpy as np
from PIL import Image
from scipy import ndimage

_rembg_session = None


def _get_rembg_session():
    global _rembg_session
    if _rembg_session is not None:
        return _rembg_session
    try:
        from rembg import new_session

        _rembg_session = new_session("u2net")
        return _rembg_session
    except Exception as error:
        print(f"rembg unavailable, using chroma fallback: {error}")
        _rembg_session = False
        return None


def _mask_with_rembg(image: Image.Image) -> np.ndarray | None:
    session = _get_rembg_session()
    if not session:
        return None
    try:
        from rembg import remove

        cut = remove(
            image.convert("RGBA"),
            session=session,
            only_mask=True,
        )
        # rembg only_mask: white subject, black background
        mask = np.asarray(cut.convert("L"), dtype=np.float32) / 255.0
        # We need background alpha: invert
        alpha = 1.0 - mask
        alpha = ndimage.gaussian_filter(alpha, sigma=1.0)
        return np.clip(alpha, 0.0, 1.0)
    except Exception as error:
        print(f"rembg mask failed: {error}")
        return None


def _skin_mask(rgb: np.ndarray) -> np.ndarray:
    r = rgb[:, :, 0]
    g = rgb[:, :, 1]
    b = rgb[:, :, 2]
    return (
        (r > 90)
        & (g > 35)
        & (b > 20)
        & (r > g)
        & (r >= b)
        & ((r - g) > 12)
    )


def _backdrop_score(color: np.ndarray) -> float:
    r, g, b = [float(x) for x in color]
    brightness = (r + g + b) / 3.0
    chroma = max(r, g, b) - min(r, g, b)
    return brightness - chroma * 1.35


def _corner_bg_color(rgb: np.ndarray, patch: int = 16) -> np.ndarray:
    h, w, _ = rgb.shape
    p = max(2, min(patch, h // 10, w // 10))
    skin = _skin_mask(rgb)
    candidates: list[np.ndarray] = []

    for y0, x0 in ((0, 0), (0, w - p), (h - p, 0), (h - p, w - p)):
        block = rgb[y0 : y0 + p, x0 : x0 + p].reshape(-1, 3)
        skin_flat = skin[y0 : y0 + p, x0 : x0 + p].reshape(-1)
        usable = block[~skin_flat]
        if len(usable) < 6:
            usable = block
        scores = np.fromiter((_backdrop_score(c) for c in usable), dtype=np.float32)
        order = np.argsort(scores)[::-1]
        top = usable[order[: max(4, len(order) // 4)]]
        candidates.append(np.median(top, axis=0))

    ranked = sorted(candidates, key=_backdrop_score, reverse=True)
    keep = ranked[:2] if len(ranked) >= 2 else ranked
    return np.median(np.array(keep, dtype=np.float32), axis=0)


def _mask_with_chroma(image: Image.Image) -> np.ndarray:
    rgb = np.asarray(image.convert("RGB"), dtype=np.float32)
    h, w, _ = rgb.shape
    bg_color = _corner_bg_color(rgb)
    dist = np.linalg.norm(rgb - bg_color, axis=2)
    skin = _skin_mask(rgb)

    border = np.zeros((h, w), dtype=bool)
    b = max(3, min(14, h // 16, w // 16))
    border[:b, :] = border[-b:, :] = border[:, :b] = border[:, -b:] = True
    border_dist = dist[border & (~skin)]
    if border_dist.size < 8:
        border_dist = dist[border]
    tolerance = float(np.percentile(border_dist, 55) + 24.0)
    tolerance = max(26.0, min(tolerance, 58.0))

    soft = 16.0
    alpha = 1.0 - np.clip((dist - (tolerance - soft)) / (2.0 * soft), 0.0, 1.0)
    alpha = alpha.astype(np.float32)
    alpha = np.where(skin, 0.0, alpha)
    alpha = ndimage.gaussian_filter(alpha, sigma=1.0)
    alpha = np.where(skin, 0.0, alpha)
    return np.clip(alpha, 0.0, 1.0)


def build_background_mask_array(image: Image.Image) -> np.ndarray:
    """
    Soft alpha mask in [0, 1], shape (H, W).
    1 = background to replace, 0 = subject to keep.
    """
    alpha = _mask_with_rembg(image)
    if alpha is None:
        alpha = _mask_with_chroma(image)
    return alpha


def build_background_mask(image: Image.Image) -> Image.Image:
    alpha = build_background_mask_array(image)
    mask = (alpha * 255.0).astype(np.uint8)
    return Image.fromarray(mask, mode="L")


def composite_background(
    subject_image: Image.Image,
    background_rgb: tuple[int, int, int] | Image.Image,
    alpha: np.ndarray | None = None,
) -> Image.Image:
    """
    Keep the subject from subject_image; replace background using alpha.
    """
    base = np.asarray(subject_image.convert("RGB"), dtype=np.float32)
    if alpha is None:
        alpha = build_background_mask_array(subject_image)
    else:
        alpha = np.asarray(alpha, dtype=np.float32)
        if alpha.max() > 1.0:
            alpha = alpha / 255.0
        alpha = np.clip(alpha, 0.0, 1.0)

    if isinstance(background_rgb, Image.Image):
        bg = np.asarray(
            background_rgb.convert("RGB").resize(
                subject_image.size, Image.Resampling.LANCZOS
            ),
            dtype=np.float32,
        )
    else:
        bg = np.empty_like(base)
        bg[:, :] = np.array(background_rgb, dtype=np.float32)

    a = alpha[..., None]
    out = base * (1.0 - a) + bg * a
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), mode="RGB")
