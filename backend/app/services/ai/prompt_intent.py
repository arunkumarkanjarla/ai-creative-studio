"""
Understand user edit prompts when a reference image is attached.

Examples:
  "change the background color to black and all other should be same"
  -> background edit, keep subject unchanged
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class EditPlan:
    mode: str  # background | preserve | restyle | transform
    strength: float
    guidance_scale: float
    change_text: str
    keep_text: str
    negative_extra: str
    solid_color: tuple[int, int, int] | None = None


_BG_WORDS = (
    "background",
    "backdrop",
    "back ground",
    "bg color",
    "bg to",
    "behind her",
    "behind him",
    "behind them",
)

_PRESERVE_WORDS = (
    "same person",
    "same face",
    "same pose",
    "same clothing",
    "same outfit",
    "same composition",
    "same image",
    "all other",
    "everything else",
    "keep same",
    "keep the same",
    "only change",
    "only the",
    "don't change",
    "do not change",
    "without changing",
)

_TRANSFORM_WORDS = (
    "completely different",
    "totally change",
    "new person",
    "different person",
    "restyle fully",
    "make it anime",
    "cartoon",
)

_COLOR_RGB = {
    "black": (0, 0, 0),
    "white": (255, 255, 255),
    "red": (200, 24, 24),
    "blue": (24, 72, 200),
    "green": (24, 140, 56),
    "yellow": (240, 210, 40),
    "pink": (235, 105, 160),
    "purple": (128, 48, 180),
    "orange": (235, 120, 30),
    "brown": (110, 70, 40),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "beige": (232, 220, 198),
    "cream": (245, 236, 220),
    "navy": (10, 25, 70),
    "maroon": (110, 20, 40),
    "gold": (212, 175, 55),
    "silver": (180, 180, 185),
}


def _has_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(p in text for p in phrases)


def _extract_solid_color(text: str) -> tuple[int, int, int] | None:
    lower = text.lower()
    # Prefer explicit "to black" / "color to black"
    for name, rgb in _COLOR_RGB.items():
        patterns = (
            rf"\bto\s+{name}\b",
            rf"\binto\s+{name}\b",
            rf"\bwith\s+{name}\b",
            rf"\bsolid\s+{name}\b",
            rf"\b{name}\s+background\b",
            rf"\bbackground(?:\s+color)?\s+{name}\b",
            rf"\bcolor\s+to\s+{name}\b",
        )
        if any(re.search(p, lower) for p in patterns):
            return rgb
    return None


def _extract_background_change(text: str) -> str:
    """Pull a short background instruction from the user prompt."""
    color = _extract_solid_color(text)
    if color is not None:
        # Reverse lookup nice name
        for name, rgb in _COLOR_RGB.items():
            if rgb == color:
                return f"solid {name} background"

    patterns = [
        r"(?:change|make|set|turn|replace)?\s*(?:the\s+)?background(?:\s+color)?\s*(?:to|into|with)?\s+([a-z0-9 \-]+)",
        r"background\s+(?:should be|as)\s+([a-z0-9 \-]+)",
        r"solid\s+([a-z]+)\s+background",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        value = " ".join(match.group(1).split())
        for stop in (
            " and ",
            " but ",
            " while ",
            " keep ",
            " same ",
            " all ",
            " everything ",
            " person ",
            " face ",
            " pose ",
        ):
            if stop in f" {value} ":
                value = value.split(stop)[0].strip()
        value = value.strip(" ,.")
        if value and value not in {"the", "a", "an", "to", "into", "with"}:
            words = value.split()
            if len(words) > 4:
                value = " ".join(words[:4])
            return f"{value} background"
    return "new studio background"


def _clean_change_focus(user_text: str, mode: str) -> str:
    text = " ".join(user_text.split())
    if mode == "background":
        return _extract_background_change(text.lower())

    cleaned = text
    for phrase in (
        "and all other should be same",
        "all other should be same",
        "same person",
        "same face",
        "same pose",
        "same clothing",
        "same composition",
        "photorealistic",
        "keep everything else same",
        "everything else same",
    ):
        cleaned = re.sub(re.escape(phrase), " ", cleaned, flags=re.IGNORECASE)
    cleaned = " ".join(cleaned.split()).strip(" ,.")
    return cleaned or text


def plan_reference_edit(user_text: str) -> EditPlan:
    """
    Decide how strongly / how to edit from the user's natural-language prompt.
    """
    raw = " ".join((user_text or "").strip().split())
    lower = raw.lower()

    is_bg = _has_any(lower, _BG_WORDS)
    is_preserve = _has_any(lower, _PRESERVE_WORDS)
    is_transform = _has_any(lower, _TRANSFORM_WORDS)

    if is_bg:
        change = _clean_change_focus(raw, "background")
        solid = _extract_solid_color(lower)
        return EditPlan(
            mode="background",
            strength=0.55,
            guidance_scale=7.5,
            change_text=change,
            keep_text="same person, same face, same hair, same pose, same clothing",
            negative_extra=(
                "different person, different face, changing face, "
                "new identity, deformed face, white background, "
                "beige background, cream background"
            ),
            solid_color=solid,
        )

    if is_preserve and not is_transform:
        change = _clean_change_focus(raw, "preserve")
        return EditPlan(
            mode="preserve",
            strength=0.28,
            guidance_scale=6.5,
            change_text=change,
            keep_text="same person, same face, same pose, same clothing, same composition",
            negative_extra=(
                "different person, different face, different pose, "
                "different clothes, warped face, identity change"
            ),
        )

    if is_transform:
        return EditPlan(
            mode="transform",
            strength=0.62,
            guidance_scale=7.0,
            change_text=raw,
            keep_text="photorealistic",
            negative_extra="blurry, low quality, deformed",
        )

    return EditPlan(
        mode="restyle",
        strength=0.40,
        guidance_scale=7.0,
        change_text=raw,
        keep_text="same person, same face, same pose, same composition",
        negative_extra="different person, different face, deformed",
    )
