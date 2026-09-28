"""
director_agent.py
------------------
FINAL AGENT: The Director

Job: assemble the fully-enriched scene list into a single render-ready 9:16 MP4:
  - Ken Burns zoom on each still image (keeps the frame feeling "alive")
  - Captions burned in at their timed positions
  - Narration audio attached per scene
  - All scenes concatenated into one continuous video

Resource safety: all moviepy clips are guaranteed to be .close()d via finally
blocks — even if write_videofile() raises an exception mid-render.
"""

from __future__ import annotations

import os

from config import settings
from core.exceptions import DirectorError
from core.logger import get_logger
from models import Caption, Scene

log = get_logger(__name__)

import re

def _is_devanagari(text: str) -> bool:
    """Return True if text contains Hindi/Devanagari characters (Unicode range 0x0900-0x097F)."""
    return any(0x0900 <= ord(char) <= 0x097F for char in text)


def _clean_caption_text(text: str) -> str:
    """Clean subtitle text by stripping markdown symbols (**bold**, _italic_, etc.) and normalizing punctuation."""
    if not text:
        return ""
    text = re.sub(r'[\*\_\#\`\~]', '', text)
    text = text.replace('—', ' - ').replace('–', ' - ')
    text = text.replace('“', '"').replace('”', '"').replace('’', "'").replace('‘', "'")
    return " ".join(text.split())


_DEFAULT_HINDI_FONTS = [
    os.path.join(settings.BASE_DIR, "assets", "NotoSansDevanagari.ttf"),
    "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf",
    os.path.join(settings.BASE_DIR, "assets", "DejaVuSans-Bold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

_DEFAULT_ENGLISH_FONTS = [
    os.path.join(settings.BASE_DIR, "assets", "DejaVuSans-Bold.ttf"),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    os.path.join(settings.BASE_DIR, "assets", "NotoSansDevanagari.ttf"),
]


def _resolve_font(text: str = "") -> str:
    """Dynamically resolve appropriate font path based on language (Hindi vs English/Latin)."""
    candidates = _DEFAULT_HINDI_FONTS if _is_devanagari(text) else _DEFAULT_ENGLISH_FONTS
    for path in candidates:
        if os.path.exists(path):
            return path

    raise DirectorError("No suitable bold font found on this system.")


def _render_caption_png(text: str, out_png_path: str, font_path: str) -> None:
    """Render Hindi/English text cleanly into a transparent PNG with background pill and stroke outline using PIL."""
    from PIL import Image, ImageDraw, ImageFont
    import textwrap

    cleaned_text = _clean_caption_text(text)
    if not cleaned_text:
        cleaned_text = "..."

    width = int(settings.VIDEO_WIDTH * 0.88)
    font_size = 50
    try:
        font = ImageFont.truetype(font_path, font_size)
    except Exception:
        font = ImageFont.load_default()

    wrapped_lines = textwrap.fill(cleaned_text, width=26).split("\n")
    line_height = int(font_size * 1.35)
    padding_v = 14
    padding_h = 24
    img_h = line_height * len(wrapped_lines) + (padding_v * 2)

    img = Image.new("RGBA", (width, img_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Calculate max line width to draw an aesthetic rounded background pill
    max_line_w = 0
    for line in wrapped_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        max_line_w = max(max_line_w, bbox[2] - bbox[0])

    pill_w = min(width, max_line_w + (padding_h * 2))
    pill_x0 = (width - pill_w) // 2
    pill_y0 = 0
    pill_x1 = pill_x0 + pill_w
    pill_y1 = img_h

    # Draw dark semi-transparent pill (alpha=180) for high-contrast reading
    draw.rounded_rectangle(
        [(pill_x0, pill_y0), (pill_x1, pill_y1)],
        radius=16,
        fill=(0, 0, 0, 180),
    )

    y = padding_v
    for line in wrapped_lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        x = (width - line_w) // 2

        # Draw bright yellow text with thick black outline for maximum readability
        draw.text(
            (x, y),
            line,
            font=font,
            fill=(255, 235, 59, 255),
            stroke_width=3,
            stroke_fill=(0, 0, 0, 255),
        )
        y += line_height

    img.save(out_png_path)


def _video_or_ken_burns_clip(media_path: str, duration: float):
    """
    If the media is an MP4, load it as a VideoFileClip and trim/loop it to the exact audio duration.
    If it's a still image (PNG/JPG), apply the Ken Burns zoom-in effect.
    """
    from moviepy import ImageClip, VideoFileClip
    import moviepy.video.fx as vfx

    if media_path.lower().endswith(".mp4"):
        clip = VideoFileClip(media_path)
        # We need to forcefully fit the video horizontally/vertically or just centre and crop
        # but replicate minimax already outputs 16:9 or 9:16. Let's force resize and crop to 9:16.
        clip = clip.resized(height=settings.VIDEO_HEIGHT)
        # If the generated clip is shorter than audio, loop it. If longer, subclip it.
        if clip.duration < duration:
            clip = clip.with_effects([vfx.Loop(duration=duration)])
        else:
            clip = clip.subclip(0, duration)
        return clip.with_position("center")
        
    else:
        # Fallback to Ken Burns for legacy offline images
        clip = ImageClip(media_path)
        scale_w = settings.VIDEO_WIDTH / clip.w
        scale_h = settings.VIDEO_HEIGHT / clip.h
        base_scale = max(scale_w, scale_h) * 1.05
        zoom_amount = 0.06

        def scale_at(t: float) -> float:
            progress = t / duration if duration > 0 else 0
            return base_scale * (1 + zoom_amount * progress)

        return clip.resized(scale_at).with_duration(duration).with_position("center")


def _caption_clip(caption: Caption, font_path: str, scene_id: int, caption_idx: int):
    """Build a timed caption clip from a PIL-rendered PNG image."""
    from moviepy import ImageClip
    import tempfile

    temp_dir = getattr(settings, "TEMP_DIR", None)
    if not isinstance(temp_dir, str) or not temp_dir:
        temp_dir = tempfile.gettempdir()

    os.makedirs(temp_dir, exist_ok=True)
    png_path = os.path.join(temp_dir, f"caption_{scene_id}_{caption_idx}.png")
    
    # Resolve dynamic language font for this specific caption
    dynamic_font_path = _resolve_font(caption.text)
    _render_caption_png(caption.text, png_path, dynamic_font_path)

    return (
        ImageClip(png_path, transparent=True)
        .with_start(caption.start)
        .with_duration(max(caption.duration(), 0.05))
        .with_position(("center", int(settings.VIDEO_HEIGHT * 0.75)))
    )


class DirectorAgent:
    def run(self, scenes: list[Scene], output_filename: str = "final_video.mp4") -> str:
        """
        Assemble all scenes into a final MP4.

        Args:
            scenes:          Fully-enriched scene list (all agents must have run).
            output_filename: Filename within OUTPUT_DIR.

        Returns:
            Absolute path to the written MP4 file.

        Raises:
            DirectorError: If any scene is missing required data or rendering fails.
        """
        from moviepy import AudioFileClip, CompositeVideoClip, concatenate_videoclips

        # Pre-flight validation
        for scene in scenes:
            if not scene.is_render_ready():
                raise DirectorError(
                    f"Scene {scene.id} is not render-ready. "
                    f"voice_ready={scene.is_voice_ready()}, "
                    f"visual_ready={scene.is_visual_ready()}, "
                    f"captions={len(scene.captions)}"
                )

        font_path = _resolve_font()
        log.info("Assembling %d scenes into final video...", len(scenes))

        scene_clips = []
        audio_clips = []
        # BUG FIX: initialise before try so the finally block and the return
        # statement are never hit with an unbound NameError if assembly fails
        # partway through (e.g. concatenate_videoclips raises).
        final = None
        out_path = ""

        try:
            for scene in scenes:
                log.debug("Scene %d: compositing (duration=%.2fs)...", scene.id, scene.duration)

                bg = _video_or_ken_burns_clip(scene.image_path, scene.duration)
                caption_clips = [
                    _caption_clip(c, font_path, scene.id, c_idx)
                    for c_idx, c in enumerate(scene.captions)
                    if c.text.strip()
                ]

                composite = CompositeVideoClip(
                    [bg, *caption_clips],
                    size=(settings.VIDEO_WIDTH, settings.VIDEO_HEIGHT),
                ).with_duration(scene.duration)

                audio = AudioFileClip(scene.audio_path)
                audio_clips.append(audio)
                composite = composite.with_audio(audio)
                scene_clips.append(composite)

            final = concatenate_videoclips(scene_clips, method="compose")
            final.mask = None
            out_path = os.path.join(settings.OUTPUT_DIR, output_filename)

            log.info("Rendering video to: %s", out_path)
            final.write_videofile(
                out_path,
                fps=settings.FPS,
                codec="libx264",
                audio_codec="aac",
                preset="medium",
                threads=4,
                logger=None,
                ffmpeg_params=["-pix_fmt", "yuv420p"],
            )

        except Exception as exc:
            raise DirectorError(f"Video assembly failed: {exc}") from exc
        finally:
            # Guarantee all clips are closed — prevents ffmpeg subprocess leaks
            for clip in scene_clips:
                try:
                    clip.close()
                except Exception:
                    pass
            for clip in audio_clips:
                try:
                    clip.close()
                except Exception:
                    pass
            if final is not None:
                try:
                    final.close()
                except Exception:
                    pass

        log.info("Video written successfully: %s", out_path)
        return out_path
