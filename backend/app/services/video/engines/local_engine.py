"""
Local CPU preview video engine.

Builds a playable MP4/WebM from character stills + edge-tts dialogue:
Ken Burns pan/zoom, amplitude-driven mouth motion, crossfades,
optional subtitles and a simple background pad.
"""
from __future__ import annotations

import asyncio
import math
import shutil
import struct
import subprocess
import wave
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFont

from app.services.video.categories import resolve_dimensions
from app.services.video.engines.base import (
    EngineCapabilities,
    EngineResult,
    ProgressCallback,
    VideoEngine,
)


def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        check=check,
        capture_output=True,
        text=True,
    )


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None


def _probe_duration(path: Path) -> float:
    result = _run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
    )
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def _load_font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ):
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _wrap_text(text: str, font: ImageFont.ImageFont, max_width: int, draw: ImageDraw.ImageDraw) -> list[str]:
    words = (text or "").split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = f"{current} {word}"
        if draw.textlength(trial, font=font) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _audio_envelope(wav_path: Path, fps: int, duration: float) -> list[float]:
    """Return per-frame amplitude 0..1 from a mono/stereo WAV."""
    frame_count = max(1, int(math.ceil(duration * fps)))
    envelope = [0.0] * frame_count
    try:
        with wave.open(str(wav_path), "rb") as wf:
            n_channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate() or 24000
            n_frames = wf.getnframes()
            raw = wf.readframes(n_frames)
    except Exception:
        return envelope

    if sampwidth == 2:
        fmt = "<" + ("h" * (len(raw) // 2))
        samples = struct.unpack(fmt, raw)
    elif sampwidth == 1:
        samples = [((b - 128) << 8) for b in raw]
    else:
        return envelope

    if n_channels > 1:
        mono = [
            sum(samples[i : i + n_channels]) / n_channels
            for i in range(0, len(samples) - n_channels + 1, n_channels)
        ]
    else:
        mono = list(samples)

    window = max(1, int(framerate / fps))
    for i in range(frame_count):
        start = i * window
        chunk = mono[start : start + window]
        if not chunk:
            envelope[i] = 0.0
            continue
        rms = math.sqrt(sum(s * s for s in chunk) / len(chunk))
        envelope[i] = min(1.0, rms / 8000.0)
    return envelope


def _cover_resize(img: Image.Image, width: int, height: int) -> Image.Image:
    src_w, src_h = img.size
    scale = max(width / src_w, height / src_h)
    new_size = (max(1, int(src_w * scale)), max(1, int(src_h * scale)))
    return img.resize(new_size, Image.Resampling.LANCZOS)


def _ken_burns_crop(
    img: Image.Image, width: int, height: int, t: float, reverse: bool = False
) -> Image.Image:
    """t in [0,1] — mild pan/zoom."""
    covered = _cover_resize(img, int(width * 1.15), int(height * 1.15))
    cw, ch = covered.size
    zoom = 1.0 + 0.08 * (t if not reverse else (1.0 - t))
    crop_w = int(width / zoom)
    crop_h = int(height / zoom)
    max_x = max(0, cw - crop_w)
    max_y = max(0, ch - crop_h)
    x = int(max_x * t)
    y = int(max_y * (1.0 - t) if reverse else max_y * t)
    cropped = covered.crop((x, y, x + crop_w, y + crop_h))
    return cropped.resize((width, height), Image.Resampling.LANCZOS)


def _draw_title_card(width: int, height: int, title: str, subtitle: str = "") -> Image.Image:
    img = Image.new("RGB", (width, height), (18, 22, 28))
    draw = ImageDraw.Draw(img)
    # Subtle gradient bars
    for i in range(height):
        shade = 18 + int(20 * (i / max(1, height - 1)))
        draw.line([(0, i), (width, i)], fill=(shade, shade + 4, shade + 10))
    title_font = _load_font(max(28, width // 22))
    sub_font = _load_font(max(18, width // 36))
    lines = _wrap_text(title or "Scene", title_font, int(width * 0.8), draw)
    y = height // 2 - len(lines) * (title_font.size + 8) // 2
    for line in lines:
        tw = draw.textlength(line, font=title_font)
        draw.text(((width - tw) / 2, y), line, fill=(245, 240, 230), font=title_font)
        y += title_font.size + 10
    if subtitle:
        sw = draw.textlength(subtitle, font=sub_font)
        draw.text(((width - sw) / 2, y + 16), subtitle, fill=(180, 190, 200), font=sub_font)
    return img


def _draw_mouth(frame: Image.Image, amplitude: float, character_name: str | None) -> None:
    """Lightweight lip-sync approximation: oval that opens with amplitude."""
    w, h = frame.size
    draw = ImageDraw.Draw(frame, "RGBA")
    cx, cy = int(w * 0.5), int(h * 0.72)
    mouth_w = int(w * 0.08)
    mouth_h = max(2, int(h * 0.01 + amplitude * h * 0.045))
    # Shadow
    draw.ellipse(
        [cx - mouth_w, cy - mouth_h, cx + mouth_w, cy + mouth_h],
        fill=(40, 10, 10, 180),
    )
    # Inner
    inner_h = max(1, int(mouth_h * 0.6))
    draw.ellipse(
        [cx - int(mouth_w * 0.7), cy - inner_h, cx + int(mouth_w * 0.7), cy + inner_h],
        fill=(120, 30, 40, 200),
    )
    if character_name:
        font = _load_font(max(14, w // 40))
        label = character_name
        tw = draw.textlength(label, font=font)
        pad = 8
        bx0, by0 = 24, h - 56
        draw.rectangle(
            [bx0, by0, bx0 + tw + pad * 2, by0 + font.size + pad],
            fill=(0, 0, 0, 150),
        )
        draw.text((bx0 + pad, by0 + pad // 2), label, fill=(255, 255, 255, 230), font=font)


async def _synthesize_tts(text: str, voice_id: str, out_mp3: Path) -> None:
    import edge_tts

    communicate = edge_tts.Communicate(text=text or " ", voice=voice_id or "en-US-JennyNeural")
    await communicate.save(str(out_mp3))


def _mp3_to_wav(mp3: Path, wav: Path) -> None:
    _run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(mp3),
            "-acodec",
            "pcm_s16le",
            "-ac",
            "1",
            "-ar",
            "24000",
            str(wav),
        ]
    )


def _write_srt(path: Path, cues: list[tuple[float, float, str]]) -> None:
    def ts(seconds: float) -> str:
        ms = int(round(seconds * 1000))
        h, rem = divmod(ms, 3600_000)
        m, rem = divmod(rem, 60_000)
        s, milli = divmod(rem, 1000)
        return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"

    lines = []
    for i, (start, end, text) in enumerate(cues, start=1):
        lines.append(str(i))
        lines.append(f"{ts(start)} --> {ts(end)}")
        lines.append(text.strip() or "...")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def _make_bg_pad(path: Path, duration: float) -> None:
    """Simple low sine pad as optional background music bed."""
    _run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=110:duration={duration}",
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=164.8:duration={duration}",
            "-filter_complex",
            "[0][1]amix=inputs=2:duration=longest,volume=0.08,afade=t=in:st=0:d=1,afade=t=out:st={0}:d=1".format(
                max(0.1, duration - 1)
            ),
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            str(path),
        ]
    )


class LocalEngine(VideoEngine):
    engine_id = "local"
    label = "Local (CPU) preview engine"
    requires_gpu = False

    def capabilities(self) -> EngineCapabilities:
        if not _ffmpeg_available():
            return EngineCapabilities(
                engine_id=self.engine_id,
                label=self.label,
                available=False,
                reason="FFmpeg/ffprobe not found on PATH",
                requires_gpu=False,
            )
        return EngineCapabilities(
            engine_id=self.engine_id,
            label=self.label,
            available=True,
            requires_gpu=False,
        )

    async def generate(
        self,
        project: Any,
        work_dir: Path,
        progress: Optional[ProgressCallback] = None,
    ) -> EngineResult:
        work_dir.mkdir(parents=True, exist_ok=True)
        frames_dir = work_dir / "frames"
        frames_dir.mkdir(exist_ok=True)

        def report(pct: int, message: str) -> None:
            if progress:
                progress(pct, message)

        report(5, "Preparing local render")

        width, height = resolve_dimensions(project.resolution, project.orientation)
        fps = int(project.fps or 24)
        # Preview engine caps FPS for CPU friendliness
        render_fps = min(fps, 24)

        scenes = list(project.scenes or [])
        characters = {c.name.lower(): c for c in (project.characters or [])}
        char_list = list(project.characters or [])

        if not scenes:
            # Single scene from top-level prompt
            class _Scene:
                prompt = project.prompt
                dialogue_text = project.prompt
                character_name = char_list[0].name if char_list else None
                duration_seconds = project.duration_seconds
                scene_index = 0

            scenes = [_Scene()]

        target_total = float(project.duration_seconds or 15)
        # Cap local preview length to keep laptop renders practical
        target_total = max(3.0, min(target_total, 60.0))
        per_scene = target_total / max(1, len(scenes))

        scene_clips: list[Path] = []
        srt_cues: list[tuple[float, float, str]] = []
        timeline = 0.0
        audio_mode = (project.audio_mode or "dialogue").lower()

        for idx, scene in enumerate(scenes):
            report(10 + int(60 * idx / max(1, len(scenes))), f"Rendering scene {idx + 1}/{len(scenes)}")
            scene_dir = work_dir / f"scene_{idx}"
            scene_dir.mkdir(exist_ok=True)

            dialogue = (scene.dialogue_text or scene.prompt or project.prompt or "").strip()
            speaker = (scene.character_name or "").strip()
            character = characters.get(speaker.lower()) if speaker else None
            if character is None and char_list:
                character = char_list[min(idx, len(char_list) - 1)]
                speaker = character.name

            voice_id = (character.voice_id if character and character.voice_id else None) or "en-US-JennyNeural"
            image_path = Path(character.image_path) if character and character.image_path else None

            desired = float(scene.duration_seconds or per_scene)
            desired = max(2.0, min(desired, per_scene * 1.5))

            audio_wav: Optional[Path] = None
            audio_mp3: Optional[Path] = None
            duration = desired

            if audio_mode in ("dialogue", "voiceover", "dialogue_music", "voiceover_music") and dialogue:
                audio_mp3 = scene_dir / "dialogue.mp3"
                audio_wav = scene_dir / "dialogue.wav"
                await _synthesize_tts(dialogue[:800], voice_id, audio_mp3)
                _mp3_to_wav(audio_mp3, audio_wav)
                duration = max(desired * 0.5, min(_probe_duration(audio_wav), max(desired, 8.0)))
                # Trim/pad audio to duration
                trimmed = scene_dir / "dialogue_trim.wav"
                _run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(audio_wav),
                        "-t",
                        f"{duration:.3f}",
                        "-af",
                        f"apad=whole_dur={duration:.3f}",
                        str(trimmed),
                    ]
                )
                audio_wav = trimmed

            if audio_mode == "silent":
                audio_wav = None

            # Base image
            if image_path and image_path.exists():
                base = Image.open(image_path).convert("RGB")
            else:
                title = scene.prompt or dialogue or f"Scene {idx + 1}"
                base = _draw_title_card(width, height, title[:120], speaker or "")

            envelope = (
                _audio_envelope(audio_wav, render_fps, duration)
                if audio_wav and audio_wav.exists()
                else [0.0] * max(1, int(duration * render_fps))
            )

            frame_count = max(1, int(math.ceil(duration * render_fps)))
            scene_frames = scene_dir / "frames"
            scene_frames.mkdir(exist_ok=True)
            reverse = idx % 2 == 1

            for fi in range(frame_count):
                t = fi / max(1, frame_count - 1)
                frame = _ken_burns_crop(base, width, height, t, reverse=reverse)
                amp = envelope[min(fi, len(envelope) - 1)] if envelope else 0.0
                if image_path and image_path.exists() and audio_mode != "silent":
                    _draw_mouth(frame, amp, speaker)
                # Soft vignette via edges
                frame.save(scene_frames / f"frame_{fi:05d}.png")
                if fi % 8 == 0:
                    await asyncio.sleep(0)  # yield

            clip_path = scene_dir / "clip.mp4"
            cmd = [
                "ffmpeg",
                "-y",
                "-framerate",
                str(render_fps),
                "-i",
                str(scene_frames / "frame_%05d.png"),
            ]
            if audio_wav and audio_wav.exists():
                cmd += ["-i", str(audio_wav), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest"]
            else:
                cmd += [
                    "-f",
                    "lavfi",
                    "-i",
                    f"anullsrc=channel_layout=stereo:sample_rate=44100",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    "-t",
                    f"{duration:.3f}",
                ]
            cmd += ["-r", str(fps), str(clip_path)]
            _run(cmd)
            scene_clips.append(clip_path)

            if dialogue:
                srt_cues.append((timeline, timeline + duration, dialogue[:200]))
            timeline += duration

            # Cleanup heavy frames early
            shutil.rmtree(scene_frames, ignore_errors=True)

        report(75, "Concatenating scenes")
        concat_list = work_dir / "concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{p.resolve().as_posix()}'" for p in scene_clips),
            encoding="utf-8",
        )
        merged = work_dir / "merged.mp4"
        _run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_list),
                "-c",
                "copy",
                str(merged),
            ]
        )

        # Crossfade-ish: re-encode with slight fade between is complex; apply overall fade in/out
        faded = work_dir / "faded.mp4"
        total_dur = _probe_duration(merged) or timeline
        fade_out_start = max(0.0, total_dur - 0.6)
        vf = f"fade=t=in:st=0:d=0.4,fade=t=out:st={fade_out_start:.3f}:d=0.5"
        af = f"afade=t=in:st=0:d=0.3,afade=t=out:st={fade_out_start:.3f}:d=0.5"

        report(82, "Applying fades and audio bed")
        bg_music = audio_mode in ("background_music", "dialogue_music", "voiceover_music", "music")
        if bg_music:
            pad = work_dir / "pad.aac"
            _make_bg_pad(pad, total_dur)
            _run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(merged),
                    "-i",
                    str(pad),
                    "-filter_complex",
                    f"[0:v]{vf}[v];[0:a]{af}[a0];[a0][1:a]amix=inputs=2:duration=first:dropout_transition=2[a]",
                    "-map",
                    "[v]",
                    "-map",
                    "[a]",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(faded),
                ]
            )
        else:
            _run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(merged),
                    "-vf",
                    vf,
                    "-af",
                    af,
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(faded),
                ]
            )

        final = faded
        if project.subtitles and srt_cues:
            report(88, "Burning subtitles")
            srt_path = work_dir / "subs.srt"
            _write_srt(srt_path, srt_cues)
            subtitled = work_dir / "subtitled.mp4"
            # Escape path for ffmpeg subtitles filter (Windows-safe-ish)
            srt_escaped = srt_path.resolve().as_posix().replace(":", "\\:")
            _run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(faded),
                    "-vf",
                    f"subtitles='{srt_escaped}':force_style='FontSize=18,PrimaryColour=&H00FFFFFF&,OutlineColour=&H00000000&,BorderStyle=3'",
                    "-c:a",
                    "copy",
                    str(subtitled),
                ]
            )
            final = subtitled

        out_ext = "webm" if (project.output_format or "mp4").lower() == "webm" else "mp4"
        output_path = work_dir / f"output.{out_ext}"
        if out_ext == "webm":
            _run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(final),
                    "-c:v",
                    "libvpx-vp9",
                    "-b:v",
                    "1M",
                    "-c:a",
                    "libopus",
                    str(output_path),
                ]
            )
        else:
            shutil.copy2(final, output_path)

        report(94, "Creating thumbnail")
        thumb_path = work_dir / "thumbnail.jpg"
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(output_path),
                "-ss",
                "0.5",
                "-vframes",
                "1",
                "-q:v",
                "3",
                str(thumb_path),
            ]
        )

        duration_seconds = _probe_duration(output_path) or total_dur
        file_size = output_path.stat().st_size
        report(100, "Local render complete")

        return EngineResult(
            output_path=output_path,
            thumbnail_path=thumb_path,
            duration_seconds=duration_seconds,
            file_size_bytes=file_size,
            metadata={"engine": "local", "fps": fps, "width": width, "height": height},
        )
