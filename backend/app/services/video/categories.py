"""Video category presets and length helpers."""

from typing import Any

CATEGORIES: dict[str, dict[str, Any]] = {
    "instagram_short": {
        "label": "Instagram Short / Reel",
        "orientation": "portrait",
        "length_preset": "short",
        "duration_seconds": 15,
        "fps": 30,
        "pacing": "fast",
    },
    "youtube_short": {
        "label": "YouTube Short",
        "orientation": "portrait",
        "length_preset": "short",
        "duration_seconds": 30,
        "fps": 30,
        "pacing": "fast",
    },
    "web_series": {
        "label": "Web Series Episode",
        "orientation": "landscape",
        "length_preset": "medium",
        "duration_seconds": 180,
        "fps": 24,
        "pacing": "medium",
    },
    "movie_short": {
        "label": "Movie / Short Film",
        "orientation": "landscape",
        "length_preset": "long",
        "duration_seconds": 600,
        "fps": 24,
        "pacing": "cinematic",
    },
    "drama": {
        "label": "Drama",
        "orientation": "landscape",
        "length_preset": "medium",
        "duration_seconds": 120,
        "fps": 24,
        "pacing": "slow",
    },
    "music_video": {
        "label": "Music Video",
        "orientation": "landscape",
        "length_preset": "medium",
        "duration_seconds": 180,
        "fps": 30,
        "pacing": "rhythmic",
    },
    "advertisement": {
        "label": "Advertisement",
        "orientation": "landscape",
        "length_preset": "short",
        "duration_seconds": 30,
        "fps": 30,
        "pacing": "punchy",
    },
    "explainer": {
        "label": "Explainer",
        "orientation": "landscape",
        "length_preset": "medium",
        "duration_seconds": 90,
        "fps": 24,
        "pacing": "clear",
    },
    "story_kids": {
        "label": "Story / Kids",
        "orientation": "landscape",
        "length_preset": "medium",
        "duration_seconds": 120,
        "fps": 24,
        "pacing": "gentle",
    },
    "documentary": {
        "label": "Documentary",
        "orientation": "landscape",
        "length_preset": "long",
        "duration_seconds": 480,
        "fps": 25,
        "pacing": "measured",
    },
    "custom": {
        "label": "Custom",
        "orientation": "landscape",
        "length_preset": "custom",
        "duration_seconds": 30,
        "fps": 24,
        "pacing": "medium",
    },
}

LENGTH_PRESETS = {
    "short": {"min": 5, "max": 60, "default": 30},
    "medium": {"min": 60, "max": 300, "default": 120},
    "long": {"min": 300, "max": 1200, "default": 600},
    "custom": {"min": 5, "max": 1200, "default": 30},
}

RESOLUTION_MAP = {
    "480p": {"landscape": (854, 480), "portrait": (480, 854), "square": (480, 480)},
    "720p": {"landscape": (1280, 720), "portrait": (720, 1280), "square": (720, 720)},
    "1080p": {"landscape": (1920, 1080), "portrait": (1080, 1920), "square": (1080, 1080)},
    "1440p": {"landscape": (2560, 1440), "portrait": (1440, 2560), "square": (1440, 1440)},
    "4k": {"landscape": (3840, 2160), "portrait": (2160, 3840), "square": (2160, 2160)},
}

GPU_ONLY_RESOLUTIONS = {"1440p", "4k"}


def resolve_dimensions(resolution: str, orientation: str) -> tuple[int, int]:
    res = RESOLUTION_MAP.get(resolution, RESOLUTION_MAP["720p"])
    return res.get(orientation, res["landscape"])


def resolve_duration(length_preset: str, category: str, custom_seconds: float | None) -> float:
    if length_preset == "custom" and custom_seconds:
        bounds = LENGTH_PRESETS["custom"]
        return max(bounds["min"], min(bounds["max"], float(custom_seconds)))
    cat = CATEGORIES.get(category, CATEGORIES["custom"])
    if custom_seconds:
        return float(custom_seconds)
    return float(cat.get("duration_seconds", 30))
