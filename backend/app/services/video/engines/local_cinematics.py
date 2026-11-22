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


def cutout_character(image_path: Path, cache_key: str | None = None) -> Image.Image:
    """
    Remove background from character portrait; return RGBA with transparent BG.
    Results cached under generated_videos/cutout_cache.
    """
    key = cache_key or hashlib.sha1(str(image_path).encode() + str(image_path.stat().st_mtime).encode()).hexdigest()
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
    zoom > 1 = push in.
    """
    # Subtle always-on breathing
    breath = 1.0 + 0.008 * math.sin(t * math.pi * 2)
    shake_x = shake_y = 0.0
    if preset == "slow_push":
        zoom = (1.05 + 0.12 * t) * breath
        ox, oy = 0.02 * t, -0.01 * t
    elif preset == "pull_out":
        zoom = (1.18 - 0.12 * t) * breath
        ox, oy = -0.02 * t, 0.01 * t
    elif preset == "pan":
        zoom = 1.1 * breath
        ox, oy = -0.08 + 0.16 * t, 0.02 * math.sin(t * math.pi)
    elif preset == "dolly":
        zoom = (1.06 + 0.1 * t) * breath
        ox, oy = 0.05 * math.sin(t * math.pi), -0.04 * t
    elif preset == "handheld":
        zoom = (1.08 + 0.04 * math.sin(t * 6)) * breath
        shake_x = 0.012 * math.sin(t * 17.3)
        shake_y = 0.01 * math.cos(t * 13.1)
        ox, oy = shake_x, shake_y
    else:
        zoom = 1.08 * breath
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
) -> tuple[int, int, int]:
    """Return (x, y, target_height) for character placement."""
    if mode == "closeup" and is_speaker:
        th = int(height * 0.92)
        x = (width - int(th * 0.7)) // 2
        y = height - th + int(8 * math.sin(t * math.pi * 2))
        return x, y, th

    if "hug" in keywords or "embrace" in keywords:
        # Move together toward center
        gather = min(1.0, t * 1.2)
        spacing = int(width * (0.22 - 0.1 * gather))
        th = int(height * 0.72)
        cx = width // 2
        if total == 1:
            return cx - int(th * 0.35), height - th, th
        side = -1 if index == 0 else 1
        x = cx + side * spacing - int(th * 0.35)
        return x, height - th, th

    if "walk" in keywords:
        # Slide in from side
        th = int(height * 0.7)
        enter = min(1.0, t * 1.5)
        start = -int(th * 0.8) if index % 2 == 0 else width
        end = int(width * (0.15 if index % 2 == 0 else 0.55))
        x = int(start + (end - start) * enter)
        return x, height - th, th

    if "celebrate" in keywords:
        th = int(height * (0.68 + 0.04 * abs(math.sin(t * math.pi * 4))))
        bounce = int(18 * abs(math.sin(t * math.pi * 4)))
        x = int(width * (0.12 + 0.4 * index))
        return x, height - th - bounce, th

    # Default two-shot / reaction
    if is_speaker:
        th = int(height * 0.78)
        x = int(width * 0.18)
    else:
        th = int(height * 0.55)
        x = int(width * 0.55)
    sway = int(6 * math.sin(t * math.pi * 2 + index))
    tilt_y = height - th + sway
    return x, tilt_y, th


def paste_character(
    canvas: Image.Image,
    cutout: Image.Image,
    x: int,
    y: int,
    target_height: int,
    *,
    amplitude: float = 0.0,
    blink: float = 0.0,
    head_tilt: float = 0.0,
    speaking: bool = False,
) -> Image.Image:
    """Composite a cutout character onto canvas; returns RGBA canvas."""
    if canvas.mode != "RGBA":
        canvas = canvas.convert("RGBA")

    aspect = cutout.width / max(1, cutout.height)
    th = max(8, target_height)
    tw = max(8, int(th * aspect))
    char = cutout.resize((tw, th), Image.Resampling.BILINEAR)

    if abs(head_tilt) > 0.1:
        char = char.rotate(head_tilt, resample=Image.Resampling.BILINEAR, expand=True)

    if speaking and amplitude > 0.02:
        _draw_mouth_rgba(char, amplitude)
    if blink > 0.5:
        _draw_blink(char)

    canvas.paste(char, (int(x), int(y)), char)
    return canvas


def _draw_mouth_rgba(char: Image.Image, amplitude: float) -> None:
    w, h = char.size
    draw = ImageDraw.Draw(char, "RGBA")
    cx, cy = int(w * 0.5), int(h * 0.70)
    mouth_w = int(w * 0.07)
    mouth_h = max(2, int(h * 0.008 + amplitude * h * 0.035))
    draw.ellipse(
        [cx - mouth_w, cy - mouth_h, cx + mouth_w, cy + mouth_h],
        fill=(50, 15, 15, 200),
    )


def _draw_blink(char: Image.Image) -> None:
    w, h = char.size
    draw = ImageDraw.Draw(char, "RGBA")
    ey = int(h * 0.42)
    for ex in (0.38, 0.62):
        cx = int(w * ex)
        draw.rectangle([cx - int(w * 0.05), ey - 2, cx + int(w * 0.05), ey + 3], fill=(30, 20, 20, 180))


def draw_particles(frame: Image.Image, t: float, kind: str, seed: int = 0) -> None:
    rng = random.Random(seed)
    draw = ImageDraw.Draw(frame, "RGBA")
    w, h = frame.size
    if kind == "confetti":
        for i in range(40):
            x = int((rng.random() * w + t * w * 0.2 * ((i % 3) - 1)) % w)
            y = int((rng.random() * h * 0.6 + t * h * (0.3 + 0.2 * (i % 5) / 5)) % h)
            color = rng.choice([(255, 80, 120, 200), (255, 200, 60, 200), (80, 180, 255, 200), (120, 255, 140, 200)])
            draw.rectangle([x, y, x + 5, y + 8], fill=color)
    elif kind == "waves":
        for i in range(5):
            y = int(h * (0.62 + 0.06 * i)) + int(6 * math.sin(t * math.pi * 2 + i))
            for x in range(0, w, 8):
                yy = y + int(4 * math.sin(x / 40 + t * 6 + i))
                draw.ellipse([x, yy, x + 10, yy + 4], fill=(200, 230, 255, 40))
    elif kind == "lamp_flicker":
        flicker = 0.7 + 0.3 * abs(math.sin(t * 25 + math.sin(t * 7)))
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        od = ImageDraw.Draw(overlay)
        gx, gy = int(w * 0.72), int(h * 0.28)
        r = int(w * 0.35 * flicker)
        od.ellipse([gx - r, gy - r, gx + r, gy + r], fill=(255, 180, 80, int(35 * flicker)))
        frame.alpha_composite(overlay)


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
