"""
Evidence render: 45s portrait 720p 24fps Drama — Ravi & Ananya (Telugu).

Saves MP4, ffprobe, contact sheet, and render time under /opt/cursor/artifacts.
Does not commit generated media.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

ARTIFACTS = Path("/opt/cursor/artifacts")
ARTIFACTS.mkdir(parents=True, exist_ok=True)


def make_project():
    ravi_img = str(ROOT / "generated_videos/characters/ravi_portrait.jpg")
    ananya_img = str(ROOT / "generated_videos/characters/ananya_portrait.jpg")

    characters = [
        SimpleNamespace(
            name="Ravi",
            voice_id="te-IN-MohanNeural",
            image_path=ravi_img,
            character_index=0,
        ),
        SimpleNamespace(
            name="Ananya",
            voice_id="te-IN-ShrutiNeural",
            image_path=ananya_img,
            character_index=1,
        ),
    ]

    scenes_spec = [
        (
            "Beach at golden hour, warm sunset sea waves",
            "ఈ సాయంత్రం చాలా అందంగా ఉంది.",  # Ravi
            "Ravi",
        ),
        (
            "Holding hands at home by a window, soft daylight",
            "నీ చేయి పట్టుకుని ఉండాలని అనిపిస్తోంది.",  # Ananya
            "Ananya",
        ),
        (
            "Studying at night at a desk with a lamp glow",
            "ఇంకా కొంచెం చదవాలి, దగ్గరపడ్డాం.",  # Ravi
            "Ravi",
        ),
        (
            "Celebrating a medical college admission result, happy success",
            "నేను సీటు సాధించాను! మనం జయించాం!",  # Ananya
            "Ananya",
        ),
        (
            "Hugging at sunset, emotional embrace together",
            "నువ్వు ఉండడం చాలా సంతోషం.",  # Ravi
            "Ravi",
        ),
    ]

    scenes = []
    for i, (prompt, dialogue, speaker) in enumerate(scenes_spec):
        scenes.append(
            SimpleNamespace(
                scene_index=i,
                prompt=prompt,
                dialogue_text=dialogue,
                character_name=speaker,
                duration_seconds=9.0,
                image_path=None,
            )
        )

    return SimpleNamespace(
        prompt="Telugu drama: Ravi and Ananya from beach golden hour to medical college celebration",
        category="drama",
        duration_seconds=45.0,
        orientation="portrait",
        resolution="720p",
        fps=24,
        audio_mode="dialogue_music",
        subtitles=True,
        output_format="mp4",
        engine="local",
        characters=characters,
        scenes=scenes,
    )


async def main():
    from app.services.video.engines.local_engine import LocalEngine

    project = make_project()
    work = ROOT / "generated_videos/work/drama_evidence"
    if work.exists():
        import shutil

        shutil.rmtree(work, ignore_errors=True)
    work.mkdir(parents=True, exist_ok=True)

    engine = LocalEngine()
    caps = engine.capabilities()
    print("capabilities:", caps)

    t0 = time.perf_counter()
    result = await engine.generate(project, work, progress=lambda p, m: print(f"[{p}%] {m}"))
    elapsed = time.perf_counter() - t0

    out_mp4 = ARTIFACTS / "drama_ravi_ananya_45s.mp4"
    import shutil

    shutil.copy2(result.output_path, out_mp4)

    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size:stream=codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate",
            "-of",
            "json",
            str(out_mp4),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    probe_path = ARTIFACTS / "drama_ravi_ananya_45s_ffprobe.json"
    probe_path.write_text(probe.stdout, encoding="utf-8")

    # Contact sheet: ~12 frames across the timeline
    sheet_dir = work / "contact_frames"
    sheet_dir.mkdir(exist_ok=True)
    duration = float(json.loads(probe.stdout)["format"]["duration"])
    times = [duration * (i + 0.5) / 12 for i in range(12)]
    thumbs = []
    for i, ts in enumerate(times):
        fp = sheet_dir / f"f{i:02d}.jpg"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-ss",
                f"{ts:.3f}",
                "-i",
                str(out_mp4),
                "-frames:v",
                "1",
                "-q:v",
                "3",
                str(fp),
            ],
            check=True,
            capture_output=True,
        )
        thumbs.append(Image.open(fp).convert("RGB"))

    # 3x4 grid contact sheet
    tw, th = thumbs[0].size
    scale = 240 / tw
    cw, ch = int(tw * scale), int(th * scale)
    sheet = Image.new("RGB", (cw * 4, ch * 3), (20, 20, 24))
    for i, im in enumerate(thumbs):
        r, c = divmod(i, 4)
        sheet.paste(im.resize((cw, ch), Image.Resampling.LANCZOS), (c * cw, r * ch))
    sheet_path = ARTIFACTS / "drama_ravi_ananya_contact_sheet.jpg"
    sheet.save(sheet_path, quality=90)

    timing = {
        "render_seconds_wall": round(elapsed, 2),
        "engine_metadata": result.metadata,
        "duration_seconds": result.duration_seconds,
        "file_size_bytes": result.file_size_bytes,
        "output": str(out_mp4),
        "ffprobe": str(probe_path),
        "contact_sheet": str(sheet_path),
        "signed_in_user_note": "Rendered via LocalEngine with same code path as authenticated Video Studio jobs",
    }
    timing_path = ARTIFACTS / "drama_ravi_ananya_render_time.json"
    timing_path.write_text(json.dumps(timing, indent=2), encoding="utf-8")
    print(json.dumps(timing, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
