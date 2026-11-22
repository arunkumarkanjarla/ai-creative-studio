"""
Local CPU cinematic preview video engine.

Builds a playable MP4/WebM from character cutouts + scene backgrounds +
edge-tts dialogue with camera motion, keyword actions, transitions, and
amplitude-driven mouth motion on the speaking character only.
"""
from __future__ import annotations

import asyncio
import math
import shutil
import struct
import subprocess
import time
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
from app.services.video.engines.local_cinematics import (
    apply_desaturate,
    apply_letterbox,
    camera_transform,
    character_layout,
    choose_motion_preset,
    cutout_character,
    detect_keywords,
    draw_particles,
    light_leak,
    paste_character,
    resolve_scene_background,
    sample_zoomed,
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
    """Soft harmonic pad as background music bed (ducked later under dialogue)."""
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
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency=220:duration={duration}",
            "-filter_complex",
            "[0][1][2]amix=inputs=3:duration=longest,volume=0.07,"
            f"afade=t=in:st=0:d=1.2,afade=t=out:st={max(0.1, duration - 1.5):.3f}:d=1.4",
            "-c:a",
            "aac",
            "-b:a",
            "96k",
            str(path),
        ]
    )


def _encode_frames_to_clip(
    frames_iter,
    clip_path: Path,
    width: int,
    height: int,
    fps: int,
    audio_wav: Optional[Path],
    duration: float,
) -> None:
    """Pipe raw RGB frames into ffmpeg — faster than writing PNG sequences."""
    video_cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "rawvideo",
        "-pix_fmt",
        "rgb24",
        "-s",
        f"{width}x{height}",
        "-r",
        str(fps),
        "-i",
        "-",
    ]
    if audio_wav and audio_wav.exists():
        video_cmd += [
            "-i",
            str(audio_wav),
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
        ]
    else:
        video_cmd += [
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-t",
            f"{duration:.3f}",
        ]
    video_cmd += ["-r", str(fps), str(clip_path)]

    proc = subprocess.Popen(
        video_cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
    )
    assert proc.stdin is not None
    err = b""
    try:
        for frame in frames_iter:
            proc.stdin.write(frame.convert("RGB").tobytes())
        proc.stdin.close()
        err = proc.stderr.read() if proc.stderr else b""
        proc.wait()
    except Exception:
        try:
            proc.kill()
        except Exception:
            pass
        raise
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg encode failed: {err[-800:].decode(errors='ignore')}"
        )


def _name_label(frame: Image.Image, name: str) -> None:
    if not name:
        return
    draw = ImageDraw.Draw(frame)
    w, h = frame.size
    font = _load_font(max(14, w // 40))
    tw = draw.textlength(name, font=font)
    pad = 8
    bx0, by0 = 24, h - 56
    draw.rectangle(
        [bx0, by0, bx0 + tw + pad * 2, by0 + font.size + pad],
        fill=(0, 0, 0),
    )
    draw.text((bx0 + pad, by0 + pad // 2), name, fill=(255, 255, 255), font=font)


class LocalEngine(VideoEngine):
    engine_id = "local"
    label = "Local (CPU) cinematic preview engine"
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
        t0 = time.perf_counter()
        work_dir.mkdir(parents=True, exist_ok=True)

        def report(pct: int, message: str) -> None:
            if progress:
                progress(pct, message)

        report(5, "Preparing cinematic local render")

        width, height = resolve_dimensions(project.resolution, project.orientation)
        fps = int(project.fps or 24)
        render_fps = min(fps, 24)

        scenes = list(project.scenes or [])
        characters = {c.name.lower(): c for c in (project.characters or [])}
        char_list = list(project.characters or [])

        if not scenes:
            class _Scene:
                prompt = project.prompt
                dialogue_text = project.prompt
                character_name = char_list[0].name if char_list else None
                duration_seconds = project.duration_seconds
                scene_index = 0
                image_path = None

            scenes = [_Scene()]

        target_total = float(project.duration_seconds or 15)
        target_total = max(3.0, min(target_total, 90.0))
        per_scene = target_total / max(1, len(scenes))

        # Precompute character cutouts (cached)
        report(8, "Cutting out characters")
        cutouts: dict[str, Image.Image] = {}
        for c in char_list:
            if c.image_path and Path(c.image_path).exists():
                cutouts[c.name.lower()] = cutout_character(Path(c.image_path))

        category = (project.category or "").lower()
        use_letterbox = category in ("drama", "movie_short", "web_series", "documentary")
        audio_mode = (project.audio_mode or "dialogue").lower()
        # Drama always gets a ducked music bed unless silent
        want_music = audio_mode in (
            "background_music",
            "dialogue_music",
            "voiceover_music",
            "music",
        ) or (category in ("drama", "movie_short", "music_video") and audio_mode != "silent")

        scene_clips: list[Path] = []
        srt_cues: list[tuple[float, float, str]] = []
        timeline = 0.0
        transitions = ("crossfade", "fade_black", "slide")

        for idx, scene in enumerate(scenes):
            report(
                10 + int(65 * idx / max(1, len(scenes))),
                f"Rendering scene {idx + 1}/{len(scenes)}",
            )
            scene_dir = work_dir / f"scene_{idx}"
            scene_dir.mkdir(exist_ok=True)

            dialogue = (scene.dialogue_text or scene.prompt or project.prompt or "").strip()
            visual_prompt = (scene.prompt or dialogue or project.prompt or "").strip()
            speaker = (scene.character_name or "").strip()
            character = characters.get(speaker.lower()) if speaker else None
            if character is None and char_list:
                character = char_list[min(idx, len(char_list) - 1)]
                speaker = character.name

            voice_id = (character.voice_id if character and character.voice_id else None) or "en-US-JennyNeural"
            keywords = detect_keywords(f"{visual_prompt} {dialogue}")
            motion = choose_motion_preset(f"{visual_prompt} {dialogue}", idx)

            desired = float(getattr(scene, "duration_seconds", None) or per_scene)
            # Honour total: keep each scene near its share of target_total
            desired = max(2.5, min(desired, per_scene * 1.35))
            # Redistribute so sum ≈ target
            if idx == len(scenes) - 1:
                desired = max(2.5, target_total - timeline)

            audio_wav: Optional[Path] = None
            duration = desired

            if audio_mode in ("dialogue", "voiceover", "dialogue_music", "voiceover_music") and dialogue:
                audio_mp3 = scene_dir / "dialogue.mp3"
                audio_wav = scene_dir / "dialogue.wav"
                await _synthesize_tts(dialogue[:800], voice_id, audio_mp3)
                _mp3_to_wav(audio_mp3, audio_wav)
                # Honour scene budget: trim long dialogue or pad short lines so
                # motion continues for the full desired duration (not a still hold).
                duration = desired
                trimmed = scene_dir / "dialogue_trim.wav"
                _run(
                    [
                        "ffmpeg",
                        "-y",
                        "-i",
                        str(audio_wav),
                        "-af",
                        f"apad=whole_dur={duration:.3f}",
                        "-t",
                        f"{duration:.3f}",
                        str(trimmed),
                    ]
                )
                audio_wav = trimmed

            if audio_mode == "silent":
                audio_wav = None

            scene_image = getattr(scene, "image_path", None)
            bg = resolve_scene_background(
                int(width * 1.3),
                int(height * 1.3),
                visual_prompt,
                scene_image,
                seed=idx * 17 + 3,
            )

            envelope = (
                _audio_envelope(audio_wav, render_fps, duration)
                if audio_wav and audio_wav.exists()
                else [0.0] * max(1, int(duration * render_fps))
            )
            frame_count = max(1, int(math.ceil(duration * render_fps)))

            # Characters present in this scene: speaker + optional second for two-shot
            scene_chars: list[Any] = []
            if character:
                scene_chars.append(character)
            for c in char_list:
                if c is character:
                    continue
                if len(scene_chars) < 2:
                    scene_chars.append(c)

            def frame_generator():
                for fi in range(frame_count):
                    t = fi / max(1, frame_count - 1)
                    zoom, ox, oy = camera_transform(t, motion, width, height)
                    # Parallax: background moves slower than characters
                    bg_frame = sample_zoomed(bg, width, height, zoom * 0.92, ox * 0.55, oy * 0.55)
                    canvas = bg_frame.convert("RGBA")

                    amp = envelope[min(fi, len(envelope) - 1)] if envelope else 0.0
                    # Close-up on speaker during louder dialogue beats
                    mode = "closeup" if amp > 0.18 else "two_shot"

                    for ci, ch in enumerate(scene_chars):
                        key = ch.name.lower()
                        cut = cutouts.get(key)
                        if cut is None:
                            continue
                        is_speaker = ch.name.lower() == (speaker or "").lower()
                        x, y, th = character_layout(
                            mode,
                            width,
                            height,
                            is_speaker=is_speaker,
                            index=ci,
                            total=len(scene_chars),
                            keywords=keywords,
                            t=t,
                        )
                        # Character parallax (slightly faster than bg)
                        x += int(ox * width * 0.35)
                        y += int(oy * height * 0.25)
                        # Breathing / sway already in layout; head tilt
                        tilt = 2.5 * math.sin(t * math.pi * 2 + ci) if is_speaker else 1.2 * math.sin(t * math.pi + ci)
                        blink = 1.0 if (fi % max(18, render_fps * 3) in (0, 1)) else 0.0
                        canvas = paste_character(
                            canvas,
                            cut,
                            x,
                            y,
                            th,
                            amplitude=amp if is_speaker else 0.0,
                            blink=blink,
                            head_tilt=tilt,
                            speaking=is_speaker and audio_mode != "silent",
                        )

                    if "celebrate" in keywords:
                        draw_particles(canvas, t, "confetti", seed=idx)
                    if "sea" in keywords or "sunset" in keywords:
                        draw_particles(canvas, t, "waves", seed=idx)
                    if "night" in keywords:
                        draw_particles(canvas, t, "lamp_flicker", seed=idx)

                    rgb = canvas.convert("RGB")
                    if "sad" in keywords:
                        rgb = apply_desaturate(rgb, 0.35 + 0.15 * t)
                    if use_letterbox:
                        rgb = apply_letterbox(rgb, 0.07)
                    if idx % 3 == 2 and t > 0.7:
                        rgb = light_leak(rgb, t, strength=0.2)

                    _name_label(rgb, speaker)
                    yield rgb

                    if fi % 12 == 0:
                        # Cooperative yield for asyncio loop
                        pass

            clip_path = scene_dir / "clip.mp4"
            # Run frame encode in thread so edge-tts event loop stays responsive
            loop = asyncio.get_event_loop()

            def _encode():
                _encode_frames_to_clip(
                    frame_generator(),
                    clip_path,
                    width,
                    height,
                    render_fps,
                    audio_wav,
                    duration,
                )

            await loop.run_in_executor(None, _encode)
            await asyncio.sleep(0)
            scene_clips.append(clip_path)

            if dialogue:
                srt_cues.append((timeline, timeline + duration, dialogue[:200]))
            timeline += duration

        # Normalize total duration toward target with a hold pad if slightly short
        if timeline < target_total - 0.4 and scene_clips:
            pad_dur = target_total - timeline
            report(78, f"Holding final scene +{pad_dur:.1f}s with motion")
            # Re-use last clip stretched via ffmpeg tpad (freeze last frame with fade)
            # Simpler: generate a short motion hold from last scene bg
            # For speed, ffmpeg tpad freeze is fine + subtle zoom via minterpolate skip
            hold = work_dir / "hold.mp4"
            _run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(scene_clips[-1]),
                    "-vf",
                    f"tpad=stop_mode=clone:stop_duration={pad_dur:.3f}",
                    "-af",
                    f"apad=pad_dur={pad_dur:.3f}",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(hold),
                ]
            )
            scene_clips[-1] = hold
            timeline += pad_dur

        report(80, "Concatenating scenes with transitions")
        # xfade between clips when few scenes; else concat copy
        merged = work_dir / "merged.mp4"
        if len(scene_clips) >= 2 and len(scene_clips) <= 8:
            # Build xfade filter chain
            inputs: list[str] = []
            for p in scene_clips:
                inputs += ["-i", str(p)]
            # Approximate offsets
            offset = 0.0
            filter_parts = []
            prev = "[0:v]"
            prev_a = "[0:a]"
            durs = [_probe_duration(p) for p in scene_clips]
            for i in range(1, len(scene_clips)):
                td = transitions[i % len(transitions)]
                fade_d = 0.45
                offset += max(0.1, durs[i - 1] - fade_d)
                vout = f"[v{i}]"
                aout = f"[a{i}]"
                if td == "fade_black":
                    # fade out/in approximated as xfade fadeblack
                    xfade = "fadeblack"
                elif td == "slide":
                    xfade = "slideleft"
                else:
                    xfade = "fade"
                filter_parts.append(
                    f"{prev}[{i}:v]xfade=transition={xfade}:duration={fade_d}:offset={offset:.3f}{vout}"
                )
                filter_parts.append(
                    f"{prev_a}[{i}:a]acrossfade=d={fade_d}{aout}"
                )
                prev, prev_a = vout, aout
            fc = ";".join(filter_parts)
            cmd = ["ffmpeg", "-y", *inputs, "-filter_complex", fc, "-map", prev, "-map", prev_a,
                   "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "-c:a", "aac",
                   str(merged)]
            result = _run(cmd, check=False)
            if result.returncode != 0:
                # Fallback to concat demuxer
                concat_list = work_dir / "concat.txt"
                concat_list.write_text(
                    "\n".join(f"file '{p.resolve().as_posix()}'" for p in scene_clips),
                    encoding="utf-8",
                )
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
        else:
            concat_list = work_dir / "concat.txt"
            concat_list.write_text(
                "\n".join(f"file '{p.resolve().as_posix()}'" for p in scene_clips),
                encoding="utf-8",
            )
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

        total_dur = _probe_duration(merged) or timeline
        # xfade shortens the timeline; pad with a motion-ish freeze so we still
        # land near the requested duration (e.g. 45 s).
        if total_dur < target_total - 0.35:
            pad_dur = target_total - total_dur
            padded = work_dir / "duration_pad.mp4"
            _run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(merged),
                    "-vf",
                    f"tpad=stop_mode=clone:stop_duration={pad_dur:.3f}",
                    "-af",
                    f"apad=pad_dur={pad_dur:.3f}",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(padded),
                ]
            )
            merged = padded
            total_dur = _probe_duration(merged) or target_total

        faded = work_dir / "faded.mp4"
        fade_out_start = max(0.0, total_dur - 0.6)
        vf = f"fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out_start:.3f}:d=0.5"
        af = f"afade=t=in:st=0:d=0.25,afade=t=out:st={fade_out_start:.3f}:d=0.5"

        report(88, "Mixing audio bed (ducked under dialogue)")
        if want_music:
            pad = work_dir / "pad.aac"
            _make_bg_pad(pad, total_dur)
            # Sidechain-ish duck: lower pad when dialogue present via volume + amix weights
            _run(
                [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(merged),
                    "-i",
                    str(pad),
                    "-filter_complex",
                    f"[0:v]{vf}[v];"
                    f"[0:a]{af},volume=1.0[a0];"
                    f"[1:a]volume=0.22[a1];"
                    f"[a0][a1]amix=inputs=2:duration=first:dropout_transition=2:weights=1 0.35[a]",
                    "-map",
                    "[v]",
                    "-map",
                    "[a]",
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
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
                    "-preset",
                    "veryfast",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(faded),
                ]
            )

        final = faded
        if project.subtitles and srt_cues:
            report(92, "Burning subtitles")
            srt_path = work_dir / "subs.srt"
            _write_srt(srt_path, srt_cues)
            subtitled = work_dir / "subtitled.mp4"
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

        report(96, "Creating thumbnail")
        thumb_path = work_dir / "thumbnail.jpg"
        _run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(output_path),
                "-ss",
                "0.8",
                "-vframes",
                "1",
                "-q:v",
                "3",
                str(thumb_path),
            ]
        )

        duration_seconds = _probe_duration(output_path) or total_dur
        file_size = output_path.stat().st_size
        render_seconds = time.perf_counter() - t0
        report(100, f"Local cinematic render complete in {render_seconds:.1f}s")

        return EngineResult(
            output_path=output_path,
            thumbnail_path=thumb_path,
            duration_seconds=duration_seconds,
            file_size_bytes=file_size,
            metadata={
                "engine": "local",
                "fps": fps,
                "width": width,
                "height": height,
                "render_seconds": round(render_seconds, 2),
                "cinematic": True,
            },
        )
