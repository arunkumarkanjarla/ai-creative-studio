"""
Cinematic helpers for the Local CPU video engine.

Backgrounds, character cutouts, motion presets, keyword actions, overlays.
"""
from __future__ import annotations

import hashlib
import math
import os
import random
import re
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

# Tunable: disable OpenVINO/diffusers scene backgrounds (slow on CPU laptops)
GENERATE_SCENE_BACKGROUNDS = os.environ.get("VIDEO_GENERATE_SCENE_BG", "0").strip() not in (
    "0",
    "false",
    "False",
    "",
)

CUTOUT_CACHE_DIR = Path(__file__).resolve().parents[4] / "generated_videos" / "cutout_cache"
CUTOUT_CACHE_DIR.mkdir(parents=True, exist_ok=True)

_MOOD_COLORS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "sunset": ((255, 120, 60), (40, 30, 80)),
    "golden": ((255, 180, 90), (60, 40, 70)),
    "beach": ((90, 180, 220), (250, 210, 140)),
    "sea": ((20, 80, 140), (80, 180, 200)),
    "wave": ((30, 90, 150), (100, 190, 210)),
    "night": ((8, 12, 40), (40, 30, 70)),
    "lamp": ((20, 15, 10), (180, 120, 40)),
    "study": ((25, 22, 35), (160, 110, 50)),
    "home": ((60, 45, 40), (200, 180, 150)),
    "window": ((70, 90, 120), (220, 200, 170)),
    "celebrate": ((255, 90, 140), (255, 200, 60)),
    "happy": ((255, 160, 80), (120, 200, 255)),
    "success": ((255, 200, 80), (80, 160, 220)),
    "hug": ((255, 140, 100), (80, 40, 60)),
    "embrace": ((255, 130, 90), (70, 35, 55)),
    "sad": ((40, 50, 70), (90, 100, 120)),
    "emotional": ((50, 40, 60), (140, 90, 100)),
    "drama": ((30, 20, 40), (120, 60, 80)),
    "default": ((35, 45, 70), (120, 100, 140)),
}


def detect_keywords(text: str) -> set[str]:
    t = (text or "").lower()
    keys = set()
    patterns = {
        "hug": r"\b(hug|embrace|holding hands|hold hands)\b",
        "celebrate": r"\b(celebrat|happy|success|admission|cheer|joy)\b",
        "walk": r"\b(walk|arriv|enter|come in|approach)\b",
        "sad": r"\b(sad|cry|tear|emotional|miss)\b",
        "night": r"\b(night|midnight|lamp|study|desk)\b",
        "sea": r"\b(sea|beach|wave|ocean|shore|golden hour)\b",
        "home": r"\b(home|window|house|room)\b",
        "sunset": r"\b(sunset|dusk|golden)\b",
    }
    for name, pat in patterns.items():
        if re.search(pat, t):
            keys.add(name)
    return keys


def pick_mood(text: str) -> str:
    keys = detect_keywords(text)
    for candidate in (
        "sunset",
        "sea",
        "night",
        "celebrate",
        "hug",
        "sad",
        "home",
        "happy",
    ):
        if candidate in keys or candidate in (text or "").lower():
            if candidate == "sea":
                return "beach"
            if candidate == "hug":
                return "embrace"
            if candidate == "celebrate":
                return "celebrate"
            if candidate == "night":
                return "night" if "study" in (text or "").lower() or "lamp" in (text or "").lower() else "night"
            return candidate
    # word hits against mood table
    low = (text or "").lower()
    for mood in _MOOD_COLORS:
        if mood in low:
            return mood
    return "default"


def procedural_background(width: int, height: int, prompt: str, seed: int = 0) -> Image.Image:
    """Mood-keyed gradient + soft bokeh circles."""
    mood = pick_mood(prompt)
    c0, c1 = _MOOD_COLORS.get(mood, _MOOD_COLORS["default"])
    rng = random.Random(seed + hash(mood) % 10000)
    arr = np.zeros((height, width, 3), dtype=np.float32)
    for y in range(height):
        t = y / max(1, height - 1)
        # Slight horizontal warmth shift
        for ch in range(3):
            arr[y, :, ch] = c0[ch] * (1 - t) + c1[ch] * t
        # Add mild horizontal vignette
        x = np.linspace(0, 1, width)
        vignette = 1.0 - 0.25 * ((x - 0.5) ** 2)
        arr[y] *= vignette[:, None]

    # Bokeh orbs
    n_orbs = 18 if mood in ("night", "lamp", "study") else 12
    for _ in range(n_orbs):
        cx = rng.randint(0, width - 1)
        cy = rng.randint(0, height - 1)
        radius = rng.randint(max(12, width // 40), max(30, width // 12))
        brightness = rng.uniform(0.15, 0.55)
        color = np.array(
            [
                min(255, c1[0] + rng.randint(-20, 60)),
                min(255, c1[1] + rng.randint(-20, 40)),
                min(255, c1[2] + rng.randint(-10, 50)),
            ],
            dtype=np.float32,
        )
        yy, xx = np.ogrid[-cy : height - cy, -cx : width - cx]
        mask = (xx * xx + yy * yy) <= radius * radius
        soft = np.clip(1.0 - np.sqrt((xx * xx + yy * yy)) / (radius + 1e-6), 0, 1)
        soft = soft * soft
        for ch in range(3):
            channel = arr[:, :, ch]
            channel[mask] = channel[mask] * (1 - soft[mask] * brightness) + color[ch] * soft[mask] * brightness

    if mood in ("night", "lamp", "study"):
        # Warm lamp glow center-right
        gx, gy = int(width * 0.72), int(height * 0.35)
        yy, xx = np.ogrid[:height, :width]
        glow = np.exp(-((xx - gx) ** 2 + (yy - gy) ** 2) / (2 * (width * 0.18) ** 2))
        arr[:, :, 0] = np.clip(arr[:, :, 0] + glow * 80, 0, 255)
        arr[:, :, 1] = np.clip(arr[:, :, 1] + glow * 45, 0, 255)

    if mood in ("beach", "sea", "wave"):
        # Horizon band
        horizon = int(height * 0.55)
        arr[horizon:, :, 2] = np.clip(arr[horizon:, :, 2] + 30, 0, 255)
        arr[:horizon, :, 0] = np.clip(arr[:horizon, :, 0] + 15, 0, 255)

    img = Image.fromarray(arr.astype(np.uint8), "RGB")
    return img.filter(ImageFilter.GaussianBlur(radius=1.2))


def try_generate_scene_background(prompt: str, width: int, height: int) -> Optional[Image.Image]:
    """Optional Image Studio pipeline background (disabled by default for laptop CPU)."""
    if not GENERATE_SCENE_BACKGROUNDS:
        return None
    try:
        from app.services.ai.image_service import generate_image_file

        result = generate_image_file(
            user_text=f"cinematic background, no people, {prompt}",
            width=min(width, 768),
            height=min(height, 768),
            steps=12,
        )
        path = result.get("path") or result.get("file_path")
        if path and Path(path).exists():
            return Image.open(path).convert("RGB")
    except Exception as exc:
        print(f"[local_engine] scene T2I background skipped: {exc}")
    return None


def resolve_scene_background(
    width: int,
    height: int,
    scene_prompt: str,
    scene_image_path: Optional[str],
    seed: int,
) -> Image.Image:
    """Priority: uploaded scene image → optional T2I → procedural mood background."""
    if scene_image_path:
        p = Path(scene_image_path)
        if p.exists():
            img = Image.open(p).convert("RGB")
            return _cover(img, width, height)

    generated = try_generate_scene_background(scene_prompt, width, height)
    if generated is not None:
        return _cover(generated, width, height)

    return procedural_background(width, height, scene_prompt, seed=seed)


def _cover(img: Image.Image, width: int, height: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(width / src_w, height / src_h)
    new_size = (max(1, int(src_w * scale)), max(1, int(src_h * scale)))
    resized = img.resize(new_size, Image.Resampling.LANCZOS)
    left = (resized.width - width) // 2
    top = (resized.height - height) // 2
    return resized.crop((left, top, left + width, top + height))


def _clean_cutout_edges(rgba: Image.Image) -> Image.Image:
    """
    Remove gray/white halo around hair: erode subject alpha, decontaminate fringe
    color, then feather.
    """
    from scipy import ndimage

    arr = np.asarray(rgba.convert("RGBA")).copy()
    rgb = arr[:, :, :3].astype(np.float32)
    alpha = arr[:, :, 3].astype(np.float32) / 255.0

    subject = alpha > 0.45
    # Pull matte inward past fringe
    eroded = ndimage.binary_erosion(subject, iterations=3)
    interior = ndimage.binary_erosion(eroded, iterations=4)
    if interior.any():
        for c in range(3):
            ch = np.where(interior, rgb[:, :, c], 0.0)
            blur = ndimage.gaussian_filter(ch, sigma=2.5)
            weight = ndimage.gaussian_filter(interior.astype(np.float32), sigma=2.5)
            filled = np.where(weight > 1e-3, blur / np.maximum(weight, 1e-3), rgb[:, :, c])
            fringe = (alpha > 0.03) & (~interior)
            rgb[:, :, c] = np.where(fringe, 0.35 * rgb[:, :, c] + 0.65 * filled, rgb[:, :, c])

    # Kill bright / gray fringe aggressively
    brightness = rgb.mean(axis=2)
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    halo = (alpha > 0.02) & (alpha < 0.97) & ((brightness > 150) | ((brightness > 120) & (chroma < 25)))
    alpha = np.where(halo, 0.0, alpha)
    alpha = np.where(eroded, alpha, 0.0)

    dist = ndimage.distance_transform_edt(alpha > 0.25)
    feather = np.clip(dist / 2.2, 0.0, 1.0)
    feather = ndimage.gaussian_filter(feather.astype(np.float32), sigma=0.55)
    alpha = np.clip(np.minimum(alpha, feather), 0.0, 1.0)

    arr[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
    arr[:, :, 3] = np.clip(alpha * 255.0, 0, 255).astype(np.uint8)
    return Image.fromarray(arr, "RGBA")


def _trim_transparent(rgba: Image.Image, pad: int = 4) -> Image.Image:
    """Crop to the opaque subject bbox so layout sizes match the person, not empty canvas."""
    arr = np.asarray(rgba.convert("RGBA"))
    alpha = arr[:, :, 3]
    ys, xs = np.where(alpha > 12)
    if len(xs) < 8:
        return rgba
    x0, x1 = max(0, xs.min() - pad), min(arr.shape[1], xs.max() + pad + 1)
    y0, y1 = max(0, ys.min() - pad), min(arr.shape[0], ys.max() + pad + 1)
    return Image.fromarray(arr[y0:y1, x0:x1], "RGBA")


def cutout_character(image_path: Path, cache_key: str | None = None) -> Image.Image:
    """
    Remove background from character portrait; return RGBA with transparent BG.
    Results cached under generated_videos/cutout_cache.
    """
    raw = (
        cache_key
        or hashlib.sha1(
            (str(image_path) + str(image_path.stat().st_mtime) + "|edge_v4").encode()
        ).hexdigest()
    )
    key = raw
    cache_path = CUTOUT_CACHE_DIR / f"{key}.png"
    if cache_path.exists():
        return Image.open(cache_path).convert("RGBA")

    src = Image.open(image_path).convert("RGBA")
    out = src
    try:
        from rembg import remove, new_session

        session = new_session("u2net")
        out = remove(src, session=session)
        if not isinstance(out, Image.Image):
            out = Image.open(out).convert("RGBA") if hasattr(out, "read") else src
        else:
            out = out.convert("RGBA")
    except Exception as exc:
        print(f"[local_engine] rembg cutout failed, using chroma fallback: {exc}")
        try:
            from app.services.ai.background_mask import build_background_mask_array

            rgb = src.convert("RGB")
            bg_alpha = build_background_mask_array(rgb)  # 1=background
            subject = (1.0 - bg_alpha) * 255.0
            rgba = np.dstack([np.asarray(rgb), subject.astype(np.uint8)])
            out = Image.fromarray(rgba, "RGBA")
        except Exception:
            out = src

    out = _clean_cutout_edges(out)
    out = _trim_transparent(out)
    out.save(cache_path)
    return out


def choose_motion_preset(prompt: str, scene_index: int) -> str:
    keys = detect_keywords(prompt)
    if "sad" in keys or "emotional" in (prompt or "").lower():
        return "slow_push"
    if "walk" in keys:
        return "pan"
    if "celebrate" in keys:
        return "handheld"
    if "sea" in keys or "sunset" in keys:
        return "dolly"
    presets = ("slow_push", "pull_out", "pan", "dolly", "handheld")
    return presets[scene_index % len(presets)]


def camera_transform(
    t: float,
    preset: str,
    width: int,
    height: int,
) -> tuple[float, float, float]:
    """
    Return (zoom, offset_x_frac, offset_y_frac) for background sampling.
    zoom > 1 = push in. Offsets kept mild so characters stay framed.
    """
    del width, height
    # Subtle always-on breathing
    breath = 1.0 + 0.006 * math.sin(t * math.pi * 2)
    if preset == "slow_push":
        zoom = (1.04 + 0.08 * t) * breath
        ox, oy = 0.012 * t, -0.008 * t
    elif preset == "pull_out":
        zoom = (1.12 - 0.08 * t) * breath
        ox, oy = -0.012 * t, 0.008 * t
    elif preset == "pan":
        zoom = 1.06 * breath
        ox, oy = -0.04 + 0.08 * t, 0.01 * math.sin(t * math.pi)
    elif preset == "dolly":
        zoom = (1.04 + 0.07 * t) * breath
        ox, oy = 0.025 * math.sin(t * math.pi), -0.02 * t
    elif preset == "handheld":
        zoom = (1.05 + 0.02 * math.sin(t * 6)) * breath
        ox = 0.006 * math.sin(t * 17.3)
        oy = 0.005 * math.cos(t * 13.1)
    else:
        zoom = 1.05 * breath
        ox, oy = 0.0, 0.0
    return zoom, ox, oy


def sample_zoomed(img: Image.Image, width: int, height: int, zoom: float, ox: float, oy: float) -> Image.Image:
    """Ken Burns style crop from a larger padded image."""
    pad = img
    if pad.size[0] < int(width * 1.25) or pad.size[1] < int(height * 1.25):
        pad = _cover(img, int(width * 1.3), int(height * 1.3))
    cw, ch = pad.size
    crop_w = max(1, int(width / max(1.0, zoom)))
    crop_h = max(1, int(height / max(1.0, zoom)))
    max_x = max(0, cw - crop_w)
    max_y = max(0, ch - crop_h)
    x = int(np.clip(max_x * (0.5 + ox), 0, max_x))
    y = int(np.clip(max_y * (0.5 + oy), 0, max_y))
    return pad.crop((x, y, x + crop_w, y + crop_h)).resize((width, height), Image.Resampling.BILINEAR)


def _safe_margins(width: int, height: int) -> tuple[int, int, int, int]:
    """left, top, right, bottom safe inset — keeps head/shoulders clear of edges/subs."""
    return (
        int(width * 0.05),
        int(height * 0.08),
        int(width * 0.05),
        int(height * 0.20),
    )


def character_layout(
    mode: str,
    width: int,
    height: int,
    *,
    is_speaker: bool,
    index: int,
    total: int,
    keywords: set[str],
    t: float,
    cutout_aspect: float = 0.75,
) -> tuple[int, int, int, int]:
    """
    Return (x, y, target_width, target_height) for character placement.

    Two-shots: side-by-side, ~40–48% frame width each, no face overlap.
    Close-ups: centered speaker with full head + shoulders in the safe area.
    """
    ml, mt, mr, mb = _safe_margins(width, height)
    safe_h = height - mt - mb
    sway = int(3 * math.sin(t * math.pi * 2 + index))

    def size_from_width_frac(frac: float, *, pair: bool = False) -> tuple[int, int]:
        tw = int(width * frac)
        # Two-shot hard cap: both characters + gap must fit in safe width
        if pair or total >= 2:
            min_gap = int(width * 0.06)
            tw = min(tw, (width - ml - mr - min_gap) // 2)
            tw = min(tw, int(width * 0.46))
        th = int(tw / max(0.45, min(cutout_aspect, 1.15)))
        min_h = int(safe_h * 0.48)
        max_h = int(safe_h * 0.70)
        if th < min_h:
            th = min_h
            tw = int(th * max(0.45, min(cutout_aspect, 1.15)))
            if pair or total >= 2:
                min_gap = int(width * 0.06)
                tw = min(tw, (width - ml - mr - min_gap) // 2, int(width * 0.46))
                th = int(tw / max(0.45, min(cutout_aspect, 1.15)))
        if th > max_h:
            th = max_h
            tw = int(th * max(0.45, min(cutout_aspect, 1.15)))
            if pair or total >= 2:
                min_gap = int(width * 0.06)
                tw = min(tw, (width - ml - mr - min_gap) // 2, int(width * 0.46))
        return tw, th

    def place_at(cx: float, tw: int, th: int, y_nudge: int = 0) -> tuple[int, int, int, int]:
        x = int(cx - tw / 2)
        # Sit above subtitle band with head well inside the top safe margin
        y = int(height * 0.78 - th) + y_nudge + sway
        x = max(ml, min(x, width - mr - tw))
        y = max(mt, min(y, height - mb - th))
        return x, y, tw, th

    # Close-up: speaker centered — keep full head inside top safe margin
    if mode == "closeup" and is_speaker:
        tw = int(width * 0.46)
        th = int(tw / max(0.45, min(cutout_aspect, 1.15)))
        th = min(th, int(safe_h * 0.62))
        tw = int(th * max(0.45, min(cutout_aspect, 1.15)))
        return place_at(width * 0.5, tw, th)

    if "hug" in keywords or "embrace" in keywords:
        gather = min(1.0, 0.25 + 0.45 * t)
        frac = 0.44 if is_speaker else 0.40
        tw, th = size_from_width_frac(frac, pair=True)
        if total == 1:
            return place_at(width * 0.5, tw, th)
        min_gap = int(width * 0.06)
        # Fixed side anchors that guarantee gap
        left_cx = ml + tw / 2
        right_cx = width - mr - tw / 2
        # Pull slightly toward center but never closer than min_gap
        max_left = width * 0.5 - (tw / 2 + min_gap / 2)
        min_right = width * 0.5 + (tw / 2 + min_gap / 2)
        if index == 0:
            cx = left_cx + (max_left - left_cx) * gather
        else:
            cx = right_cx + (min_right - right_cx) * gather
        return place_at(cx, tw, th)

    if "walk" in keywords:
        frac = 0.45 if is_speaker else 0.40
        tw, th = size_from_width_frac(frac, pair=True)
        enter = min(1.0, 0.2 + t * 1.15)
        end_cx = ml + tw / 2 if index == 0 else width - mr - tw / 2
        # Keep partial character visible during entrance
        if index == 0:
            start_cx = ml + tw * 0.35
        else:
            start_cx = width - mr - tw * 0.35
        cx = start_cx + (end_cx - start_cx) * enter
        return place_at(cx, tw, th)

    if "celebrate" in keywords:
        bounce = int(8 * abs(math.sin(t * math.pi * 4)))
        frac = 0.45 if is_speaker else 0.40
        tw, th = size_from_width_frac(frac, pair=True)
        cx = ml + tw / 2 if index == 0 else width - mr - tw / 2
        return place_at(cx, tw, th, y_nudge=-bounce)

    if total <= 1:
        tw, th = size_from_width_frac(0.48 if is_speaker else 0.44, pair=False)
        return place_at(width * 0.5, tw, th)

    # Default two-shot: speaker slightly larger / forward
    frac = 0.46 if is_speaker else 0.40
    tw, th = size_from_width_frac(frac, pair=True)
    cx = ml + tw / 2 if is_speaker else width - mr - tw / 2
    # If listener somehow index 0 without is_speaker — keep right
    if not is_speaker:
        cx = width - mr - tw / 2
    else:
        cx = ml + tw / 2
    y_nudge = -8 if is_speaker else 12
    return place_at(cx, tw, th, y_nudge=y_nudge)


def paste_character(
    canvas: Image.Image,
    cutout: Image.Image,
    x: int,
    y: int,
    target_height: int,
    *,
    target_width: int | None = None,
    amplitude: float = 0.0,
    blink: float = 0.0,
    head_tilt: float = 0.0,
    speaking: bool = False,
) -> Image.Image:
    """Composite a cutout character onto canvas; returns RGBA canvas."""
    if canvas.mode != "RGBA":
        canvas = canvas.convert("RGBA")

    aspect = cutout.width / max(1, cutout.height)
    if target_width is not None:
        tw = max(8, target_width)
        th = max(8, int(tw / max(0.35, aspect)))
    else:
        th = max(8, target_height)
        tw = max(8, int(th * aspect))
    char = cutout.resize((tw, th), Image.Resampling.LANCZOS)

    if abs(head_tilt) > 0.1:
        char = char.rotate(head_tilt, resample=Image.Resampling.BILINEAR, expand=True)

    if speaking and amplitude > 0.05:
        _draw_mouth_rgba(char, amplitude)
    # Intentionally skip hard blink rectangles — they read as face artifacts.

    # Final clamp — keep head/shoulders inside the frame
    cw, ch = canvas.size
    x = max(0, min(int(x), max(0, cw - char.width)))
    y = max(0, min(int(y), max(0, ch - int(char.height * 0.92))))
    canvas.paste(char, (x, y), char)
    return canvas


def _draw_mouth_rgba(char: Image.Image, amplitude: float) -> None:
    """Very subtle lip cue — keep small so it doesn't look like a sticker."""
    w, h = char.size
    draw = ImageDraw.Draw(char, "RGBA")
    cx, cy = int(w * 0.5), int(h * 0.72)
    mouth_w = max(3, int(w * 0.045))
    mouth_h = max(1, int(h * 0.004 + amplitude * h * 0.018))
    draw.ellipse(
        [cx - mouth_w, cy - mouth_h, cx + mouth_w, cy + mouth_h],
        fill=(60, 20, 25, 110),
    )


def draw_particles(frame: Image.Image, t: float, kind: str, seed: int = 0) -> None:
    rng = random.Random(seed)
    draw = ImageDraw.Draw(frame, "RGBA")
    w, h = frame.size
    if kind == "confetti":
        # Keep particles in the upper sky — never across faces
        for i in range(36):
            x = int((rng.random() * w + t * w * 0.15 * ((i % 3) - 1)) % w)
            y = int(rng.random() * h * 0.42)
            color = rng.choice(
                [(255, 80, 120, 180), (255, 200, 60, 180), (80, 180, 255, 180), (120, 255, 140, 180)]
            )
            draw.rectangle([x, y, x + 4, y + 7], fill=color)
    elif kind == "waves":
        # No foreground stroke lines — sea motion is handled by background shimmer.
        return
    elif kind == "lamp_flicker":
        flicker = 0.7 + 0.3 * abs(math.sin(t * 25 + math.sin(t * 7)))
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        gx, gy = int(w * 0.72), int(h * 0.28)
        r = int(w * 0.35 * flicker)
        od.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(255, 180, 80, int(35 * flicker)))
        frame.alpha_composite(overlay)


def apply_sea_shimmer(bg: Image.Image, t: float) -> Image.Image:
    """
    Subtle water motion in the lower background only — never draws strokes over subjects.
    """
    arr = np.asarray(bg.convert("RGB")).astype(np.float32)
    h, w, _ = arr.shape
    y0 = int(h * 0.58)
    band = arr[y0:, :, :]
    yy = np.arange(band.shape[0])[:, None]
    xx = np.arange(band.shape[1])[None, :]
    ripple = 4.0 * np.sin(xx / 28.0 + t * 5.0) * np.sin(yy / 18.0 + t * 3.0)
    # Horizontal pixel shift via roll per row (cheap fake refraction)
    out = band.copy()
    for i in range(0, band.shape[0], 2):
        shift = int(ripple[i, band.shape[1] // 2])
        if shift:
            out[i] = np.roll(band[i], shift, axis=0)
    # Soft blue lift
    out[:, :, 2] = np.clip(out[:, :, 2] + 6 + 4 * np.sin(t * 4), 0, 255)
    arr[y0:] = out
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def apply_desaturate(frame: Image.Image, amount: float) -> Image.Image:
    if amount <= 0:
        return frame
    enhancer = ImageEnhance.Color(frame)
    return enhancer.enhance(max(0.0, 1.0 - amount))


def apply_letterbox(frame: Image.Image, bar_frac: float = 0.08) -> Image.Image:
    w, h = frame.size
    bar = int(h * bar_frac)
    draw = ImageDraw.Draw(frame)
    draw.rectangle([0, 0, w, bar], fill=(0, 0, 0))
    draw.rectangle([0, h - bar, w, h], fill=(0, 0, 0))
    return frame


def light_leak(frame: Image.Image, t: float, strength: float = 0.25) -> Image.Image:
    w, h = frame.size
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    x = int(w * (0.2 + 0.6 * abs(math.sin(t * math.pi))))
    draw.ellipse([x - w // 4, -h // 8, x + w // 4, h // 3], fill=(255, 200, 140, int(90 * strength)))
    if frame.mode != "RGBA":
        base = frame.convert("RGBA")
        base.alpha_composite(overlay)
        return base.convert("RGB")
    frame.alpha_composite(overlay)
    return frame


def crossfade_frames(a: Image.Image, b: Image.Image, u: float) -> Image.Image:
    u = max(0.0, min(1.0, u))
    return Image.blend(a.convert("RGB"), b.convert("RGB"), u)
