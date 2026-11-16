"""
Build short, CLIP-safe prompts for Realistic Vision.

CLIP max = 77 tokens.
- No reference selected  -> use the user prompt only
- Reference selected     -> apply saved style + user prompt
"""

from __future__ import annotations

from app.services.ai.prompt_store import (
    DEFAULT_NEGATIVE,
    load_meta,
)


def _approx_tokens(text: str) -> int:
    return max(1, len(text.split()) + text.count(",") + 2)


def truncate_prompt(text: str, max_tokens: int = 70) -> str:
    text = " ".join(text.split())
    if _approx_tokens(text) <= max_tokens:
        return text

    parts = [p.strip() for p in text.split(",") if p.strip()]
    kept: list[str] = []
    for part in parts:
        trial = ", ".join(kept + [part])
        if _approx_tokens(trial) > max_tokens:
            break
        kept.append(part)

    if kept:
        return ", ".join(kept)

    words = text.split()
    return " ".join(words[: max_tokens - 2])


def clean_user_text(user_text: str) -> str:
    text = " ".join(user_text.strip().split())
    blocked = ["nude", "nsfw", "explicit"]
    lower = text.lower()
    for word in blocked:
        if word in lower:
            text = text.replace(word, "")
            text = text.replace(word.title(), "")
    return " ".join(text.split())


def build_prompts(
    user_text: str,
    prompt_id: str | None = None,
) -> tuple[str, str, str | None]:
    """
    Returns: (final_prompt, negative_prompt, used_prompt_id)

    Reference is optional:
    - if prompt_id is missing/invalid -> user text only
    - if prompt_id exists -> style base + user text
    """
    user_text = clean_user_text(user_text)
    if not user_text:
        user_text = "high quality photo"

    style = load_meta(prompt_id) if prompt_id else None

    if style:
        base = (style.get("base_prompt") or "").strip()
        negative = style.get("negative_prompt") or DEFAULT_NEGATIVE
        used_id = style.get("prompt_id")

        if base:
            # Keep style short + append user request
            if _approx_tokens(user_text) <= 30:
                final = f"{base}, {user_text}"
            else:
                short = ", ".join(user_text.split(",")[:3])
                final = f"{base}, {short}"
        else:
            final = user_text
    else:
        # No reference selected: do not force any women/saree style
        used_id = None
        negative = DEFAULT_NEGATIVE
        final = f"{user_text}, RAW photo, natural lighting, high detail"

    final = truncate_prompt(final, max_tokens=70)
    negative = truncate_prompt(negative, max_tokens=70)
    return final, negative, used_id
