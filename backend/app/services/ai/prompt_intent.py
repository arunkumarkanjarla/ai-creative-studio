"""
Understand user edit prompts when a reference image is attached.

Works for people, animals, objects, and scenes — no human-only assumptions.
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
    "behind it",
)

_PRESERVE_WORDS = (
    "same person",
    "same face",
    "same pose",
    "same clothing",
    "same outfit",
    "same composition",
    "same image",
    "same bird",
    "same animal",
    "same object",
    "same subject",
    "original",
    "all other",
    "everything else",
    "keep same",
    "keep the same",
    "should be same",
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

_HUMAN_WORDS = (
    "person",
    "people",
    "human",
    "man",
    "woman",
    "girl",
    "boy",
    "face",
    "portrait",
    "hair",
    "clothing",
    "saree",
    "dress",
)

_ANIMAL_WORDS = (
    "bird",
    "parrot",
    "dog",
    "cat",
    "animal",
    "pet",
    "horse",
    "cow",
    "tiger",
    "lion",
    "elephant",
    "fish",
    "wildlife",
)

_OBJECT_WORDS = (
    "car",
    "bike",
    "building",
    "product",
    "object",
    "furniture",
    "phone",
    "bottle",
    "food",
    "flower",
    "tree",
    "landscape",
)

# Longer / multi-word colors first
_COLOR_RGB = {
    "sky blue": (135, 206, 235),
    "light blue": (173, 216, 230),
    "dark blue": (0, 51, 102),
    "navy blue": (10, 25, 70),
    "light green": (144, 238, 144),
    "dark green": (0, 100, 0),
    "light gray": (200, 200, 200),
    "light grey": (200, 200, 200),
    "dark gray": (64, 64, 64),
    "dark grey": (64, 64, 64),
    "off white": (250, 250, 245),
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


def _subject_kind(text: str) -> str:
    """Return human | animal | object | generic from the user's words."""
    if _has_any(text, _HUMAN_WORDS):
        return "human"
    if _has_any(text, _ANIMAL_WORDS):
        return "animal"
    if _has_any(text, _OBJECT_WORDS):
        return "object"
    return "generic"


def _extract_user_keep_phrases(text: str) -> str | None:
    """
    Prefer the user's own preserve wording, e.g.
    'same original bird should be same' -> 'same original bird'
    """
    stop = {
        "should",
        "be",
        "but",
        "and",
        "as",
        "the",
        "a",
        "an",
        "to",
        "with",
        "now",
        "having",
        "all",
        "other",
        "everything",
        "else",
        "image",
        "photo",
        "picture",
    }
    phrases: list[str] = []

    for match in re.finditer(
        r"same\s+(?:original\s+)?([a-z0-9\-]+(?:\s+[a-z0-9\-]+){0,2})",
        text,
        flags=re.IGNORECASE,
    ):
        words = match.group(0).lower().split()
        cleaned: list[str] = []
        for word in words:
            if word in stop and cleaned:
                break
            if word in stop:
                continue
            cleaned.append(word)
        if len(cleaned) >= 2:
            phrases.append(" ".join(cleaned))

    for match in re.finditer(
        r"original\s+([a-z0-9\-]+)",
        text,
        flags=re.IGNORECASE,
    ):
        noun = match.group(1).lower()
        if noun not in stop:
            phrases.append(f"same original {noun}")

    seen: set[str] = set()
    unique: list[str] = []
    for item in phrases:
        # Prefer shorter specific phrases over longer duplicates
        if any(item != other and item in other for other in phrases):
            continue
        if item not in seen:
            seen.add(item)
            unique.append(item)

    if not unique:
        return None
    return ", ".join(unique[:3])


def _default_keep_text(kind: str) -> str:
    if kind == "human":
        return "same subject, same person, same face, same pose, same clothing"
    if kind == "animal":
        return "same animal, same subject, same pose, same details, unchanged"
    if kind == "object":
        return "same object, same subject, same shape, same details, unchanged"
    return "same subject, same details, same composition, keep original unchanged"


def _default_negative(kind: str, mode: str) -> str:
    common = "blurry, low quality, deformed, watermark, text"
    if mode == "background":
        bg_neg = "wrong background, unchanged white background"
    else:
        bg_neg = ""

    if kind == "human":
        subject_neg = (
            "different person, different face, changing identity, warped face"
        )
    elif kind == "animal":
        subject_neg = (
            "different animal, different species, changed bird, "
            "changed animal, human face, person"
        )
    elif kind == "object":
        subject_neg = "different object, changed product, warped shape, person"
    else:
        subject_neg = (
            "different subject, changed identity, unwanted person, "
            "unwanted face replacement"
        )

    parts = [p for p in (subject_neg, bg_neg, common) if p]
    return ", ".join(parts)


def _extract_solid_color(text: str) -> tuple[int, int, int] | None:
    lower = text.lower()
    # Multi-word colors first
    for name, rgb in _COLOR_RGB.items():
        patterns = (
            rf"\bto\s+{re.escape(name)}\b",
            rf"\binto\s+{re.escape(name)}\b",
            rf"\bwith\s+{re.escape(name)}\b",
            rf"\bsolid\s+{re.escape(name)}\b",
            rf"\b{re.escape(name)}\s+background\b",
            rf"\bbackground(?:\s+color)?\s+(?:to\s+)?{re.escape(name)}\b",
            rf"\bcolor\s+to\s+{re.escape(name)}\b",
            rf"\bas\s+now\s+having\b.*\bto\s+{re.escape(name)}\b",
        )
        if any(re.search(p, lower) for p in patterns):
            return rgb
    return None


def _extract_background_change(text: str) -> str:
    """Pull a short background instruction from the user prompt."""
    color = _extract_solid_color(text)
    if color is not None:
        for name, rgb in _COLOR_RGB.items():
            if rgb == color:
                return f"{name} background"

    patterns = [
        r"(?:change|make|set|turn|replace)?\s*(?:the\s+)?background(?:\s+color)?\s*(?:to|into|with)?\s+([a-z0-9 \-]+)",
        r"background\s+(?:should be|as)\s+([a-z0-9 \-]+)",
        r"solid\s+([a-z ]+)\s+background",
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
            " as ",
            " original ",
            " person ",
            " face ",
            " pose ",
            " bird ",
            " animal ",
        ):
            if stop in f" {value} ":
                value = value.split(stop)[0].strip()
        value = value.strip(" ,.")
        # Drop trailing filler words
        while value.split() and value.split()[-1] in {
            "as",
            "now",
            "having",
            "the",
            "a",
            "an",
            "to",
            "into",
            "with",
            "color",
        }:
            value = " ".join(value.split()[:-1]).strip()
        if value and value not in {"the", "a", "an", "to", "into", "with"}:
            words = value.split()
            if len(words) > 4:
                value = " ".join(words[:4])
            if "background" not in value:
                return f"{value} background"
            return value
    return "new background"


def _clean_change_focus(user_text: str, mode: str) -> str:
    text = " ".join(user_text.split())
    if mode == "background":
        return _extract_background_change(text.lower())

    cleaned = text
    for phrase in (
        "and all other should be same",
        "all other should be same",
        "should be same",
        "same person",
        "same face",
        "same pose",
        "same clothing",
        "same composition",
        "same bird",
        "same animal",
        "same object",
        "same subject",
        "photorealistic",
        "keep everything else same",
        "everything else same",
        "original bird",
        "original animal",
        "original subject",
    ):
        cleaned = re.sub(re.escape(phrase), " ", cleaned, flags=re.IGNORECASE)
    cleaned = " ".join(cleaned.split()).strip(" ,.")
    return cleaned or text


def plan_reference_edit(user_text: str) -> EditPlan:
    """
    Decide how strongly / how to edit from the user's natural-language prompt.
    Keep language subject-agnostic unless the user clearly mentions a human.
    """
    raw = " ".join((user_text or "").strip().split())
    lower = raw.lower()

    kind = _subject_kind(lower)
    user_keep = _extract_user_keep_phrases(lower)
    keep_text = user_keep or _default_keep_text(kind)

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
            keep_text=keep_text,
            negative_extra=_default_negative(kind, "background"),
            solid_color=solid,
        )

    if is_preserve and not is_transform:
        change = _clean_change_focus(raw, "preserve")
        return EditPlan(
            mode="preserve",
            strength=0.28,
            guidance_scale=6.5,
            change_text=change,
            keep_text=keep_text,
            negative_extra=_default_negative(kind, "preserve"),
        )

    if is_transform:
        return EditPlan(
            mode="transform",
            strength=0.62,
            guidance_scale=7.0,
            change_text=raw,
            keep_text="photorealistic",
            negative_extra=_default_negative(kind, "transform"),
        )

    return EditPlan(
        mode="restyle",
        strength=0.40,
        guidance_scale=7.0,
        change_text=raw,
        keep_text=keep_text,
        negative_extra=_default_negative(kind, "restyle"),
    )
