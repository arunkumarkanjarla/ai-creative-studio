"""
Build short, CLIP-safe prompts for Realistic Vision.

CLIP max = 77 tokens.
- No reference selected  -> use the user prompt only
- Reference selected     -> interpret edit intent without forcing human/portrait terms
"""

from __future__ import annotations

from app.services.ai.prompt_intent import plan_reference_edit
from app.services.ai.prompt_store import (
    DEFAULT_NEGATIVE,
    find_reference_file,
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
) -> tuple[str, str, str | None, dict | None]:
    """
    Returns: (final_prompt, negative_prompt, used_prompt_id, edit_plan_dict)
    """
    user_text = clean_user_text(user_text)
    if not user_text:
        user_text = "high quality photo"

    style = load_meta(prompt_id) if prompt_id else None
    has_reference = bool(prompt_id and find_reference_file(prompt_id))
    edit_plan = None

    if has_reference:
        plan = plan_reference_edit(user_text)
        edit_plan = {
            "mode": plan.mode,
            "strength": plan.strength,
            "guidance_scale": plan.guidance_scale,
            "change_text": plan.change_text,
            "keep_text": plan.keep_text,
            "negative_extra": plan.negative_extra,
            "solid_color": plan.solid_color,
        }

        if plan.mode == "background":
            # Only the requested background + subject preservation (no portrait bias)
            final = (
                f"{plan.change_text}, {plan.keep_text}, "
                f"photorealistic, sharp detail"
            )
        elif plan.mode == "preserve":
            final = (
                f"{plan.change_text}, {plan.keep_text}, "
                f"photorealistic, natural lighting"
            )
        else:
            final = (
                f"{plan.change_text}, {plan.keep_text}, "
                f"photorealistic, natural lighting"
            )

        base_negative = (style or {}).get("negative_prompt") or DEFAULT_NEGATIVE
        negative = f"{plan.negative_extra}, {base_negative}"
        used_id = prompt_id
    elif style:
        base = (style.get("base_prompt") or "").strip()
        negative = style.get("negative_prompt") or DEFAULT_NEGATIVE
        used_id = style.get("prompt_id")

        if base:
            if _approx_tokens(user_text) <= 30:
                final = f"{base}, {user_text}"
            else:
                short = ", ".join(user_text.split(",")[:3])
                final = f"{base}, {short}"
        else:
            final = user_text
    else:
        used_id = None
        negative = DEFAULT_NEGATIVE
        final = f"{user_text}, RAW photo, natural lighting, high detail"

    final = truncate_prompt(final, max_tokens=70)
    negative = truncate_prompt(negative, max_tokens=70)
    return final, negative, used_id, edit_plan
