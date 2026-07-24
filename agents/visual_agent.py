"""
visual_agent.py
----------------
AGENT 3: The Cinematographer

Job: turn each scene's visual_prompt into an image file the Director agent
can later animate (Ken Burns pan/zoom) into the final video.

LIVE MODE : Gemini image generation API.
            API call is retried with exponential backoff.
DEMO MODE : Renders a mood-tinted gradient card with PIL — proves the full
            pipeline's timing/sync/assembly logic with zero API cost.

PERFORMANCE: All scenes are processed concurrently via ThreadPoolExecutor.
"""

from __future__ import annotations

import base64
import os
import textwrap
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import settings
from core.exceptions import VisualError
from core.logger import get_logger
from core.retry import retry_api_call
from models import Scene

log = get_logger(__name__)


# ── Mood colour palette for offline cards ─────────────────────────────────────

_MOOD_COLORS: dict[str, tuple[tuple[int, int, int], tuple[int, int, int]]] = {
    "tense":    ((40,  10,  10),  (120, 20,  20)),
    "romantic": ((60,  10,  40),  (200, 80,  130)),
    "joyful":   ((255, 190, 60),  (255, 110, 60)),
    "ominous":  ((10,  10,  25),  (40,  40,  70)),
    "calm":     ((20,  50,  70),  (60,  130, 160)),
    "neutral":  ((30,  30,  40),  (70,  70,  90)),
}

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]


# ── Live provider: Gemini image gen ──────────────────────────────────────────

@retry_api_call(
    max_attempts=settings.API_MAX_RETRIES,
    base_delay=settings.API_BASE_DELAY,
)
def _call_gemini_image(prompt: str, out_path: str) -> None:
    import requests

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-3.1-flash-image:generateContent?key={settings.GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    resp = requests.post(url, json=payload, timeout=90)
    resp.raise_for_status()
    data = resp.json()

    b64_img = data["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
    with open(out_path, "wb") as f:
        f.write(base64.b64decode(b64_img))

    if not os.path.exists(out_path) or os.path.getsize(out_path) == 0:
        raise VisualError(f"Gemini image gen wrote an empty file at: {out_path}")


# ── Offline fallback: PIL gradient card ──────────────────────────────────────

def _load_font(size: int = 46):
    """Try system fonts in order; fall back to PIL default."""
    from PIL import ImageFont
    for path in _FONT_CANDIDATES:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _offline_image(prompt: str, mood: str, out_path: str) -> None:
    """Render a mood-tinted gradient card with the scene prompt as overlay text."""
    from PIL import Image, ImageDraw

    size = (settings.VIDEO_WIDTH, settings.VIDEO_HEIGHT)
    top_color, bottom_color = _MOOD_COLORS.get(mood, _MOOD_COLORS["neutral"])

    # Build vertical gradient
    img = Image.new("RGB", size, top_color)
    draw = ImageDraw.Draw(img)
    w, h = size
    for y in range(h):
        t = y / h
        r = int(top_color[0] + (bottom_color[0] - top_color[0]) * t)
        g = int(top_color[1] + (bottom_color[1] - top_color[1]) * t)
        b = int(top_color[2] + (bottom_color[2] - top_color[2]) * t)
        draw.line([(0, y), (w, y)], fill=(r, g, b))

    font = _load_font(46)
    wrapped = textwrap.fill(prompt, width=22)
    lines = wrapped.split("\n")
    line_height = 60
    total_h = len(lines) * line_height
    y = (size[1] - total_h) // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        draw.text(((w - line_w) // 2, y), line, font=font, fill=(255, 255, 255))
        y += line_height

    img.save(out_path)


import hashlib
import shutil

def _get_cache_path(prompt: str) -> str:
    cache_dir = os.path.join(settings.TEMP_DIR, "cache_images")
    os.makedirs(cache_dir, exist_ok=True)
    prompt_hash = hashlib.md5(prompt.encode("utf-8")).hexdigest()
    return os.path.join(cache_dir, f"{prompt_hash}.png")


def _call_pollinations_image(prompt: str, out_path: str) -> None:
    """Generate high-quality AI images via Pollinations Turbo (uses 540x960 and fast 10s timeout for stability)."""
    import urllib.parse
    import requests
    import random

    styled_prompt = f"cinematic movie still, {prompt}, photorealistic, dramatic lighting"
    encoded_prompt = urllib.parse.quote(styled_prompt)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    last_exc = None
    for attempt in range(2):
        seed = random.randint(1000, 999999)
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=540&height=960&model=turbo&nologo=true&seed={seed}"
        try:
            resp = requests.get(url, headers=headers, timeout=10)
            resp.raise_for_status()
            with open(out_path, "wb") as f:
                f.write(resp.content)
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                return
        except Exception as exc:
            last_exc = exc

    raise VisualError(f"Pollinations turbo image gen failed: {last_exc}")


def _call_stock_image(prompt: str, out_path: str) -> None:
    """Fallback photo generator using high-resolution seed images."""
    import requests
    seed = abs(hash(prompt)) % 1000
    url = f"https://picsum.photos/seed/{seed}/1080/1920"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    with open(out_path, "wb") as f:
        f.write(resp.content)


# ── Per-scene worker ──────────────────────────────────────────────────────────

def _process_scene(scene: Scene) -> Scene:
    """Generate an image for a single scene with caching and rate-limit fallbacks."""
    out_path = os.path.join(settings.TEMP_DIR, f"scene_{scene.id}.png")
    cache_path = _get_cache_path(scene.visual_prompt)

    # 1. Check local cache first to avoid duplicate API calls
    if os.path.exists(cache_path) and os.path.getsize(cache_path) > 0:
        log.info("Scene %d: using cached visual prompt image.", scene.id)
        shutil.copyfile(cache_path, out_path)
        scene.image_path = out_path
        return scene

    try:
        if settings.USE_LIVE_IMAGE_GEN:
            log.debug("Scene %d: calling Gemini image gen.", scene.id)
            _call_gemini_image(scene.visual_prompt, out_path)
        else:
            raise VisualError("USE_LIVE_IMAGE_GEN is False")
    except Exception as exc:
        log.info(
            "Scene %d: Gemini image gen unavailable (%s) — generating AI image via Pollinations Turbo.",
            scene.id,
            exc,
        )
        try:
            _call_pollinations_image(scene.visual_prompt, out_path)
        except Exception as p_exc:
            log.warning(
                "Scene %d: Pollinations AI failed (%s) — fetching stock photo scene.",
                scene.id,
                p_exc,
            )
            try:
                _call_stock_image(scene.visual_prompt, out_path)
            except Exception as s_exc:
                log.warning("Scene %d: Stock photo failed (%s) — using gradient card.", scene.id, s_exc)
                _offline_image(scene.visual_prompt, scene.mood, out_path)

    # Cache successful image output
    if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
        try:
            shutil.copyfile(out_path, cache_path)
        except Exception:
            pass

    # Sanity check — make sure a file actually exists before continuing
    if not os.path.exists(out_path):
        raise VisualError(f"Scene {scene.id}: no image file produced at '{out_path}'.")

    scene.image_path = out_path
    return scene


# ── Agent ─────────────────────────────────────────────────────────────────────

class VisualAgent:
    def run(self, scenes: list[Scene]) -> list[Scene]:
        """
        Generate images for all scenes concurrently.

        Args:
            scenes: Scene list from VoiceAgent (audio_path + duration already set).

        Returns:
            The same list with `image_path` populated on each scene.

        Raises:
            VisualError: If any scene fails image generation entirely.
        """
        # Process sequentially with polite delay to avoid rate limiting on image APIs
        max_workers = 1
        errors: list[str] = []

        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="visual") as pool:
            futures = {pool.submit(_process_scene, scene): scene for scene in scenes}
            for future in as_completed(futures):
                scene = futures[future]
                try:
                    future.result()
                    log.info("Scene %d: image ready → %s", scene.id, scene.image_path)
                except Exception as exc:
                    errors.append(f"Scene {scene.id}: {exc}")
                    log.error("Scene %d: image generation FAILED — %s", scene.id, exc)

        if errors:
            raise VisualError(
                f"{len(errors)} scene(s) failed image generation:\n" + "\n".join(errors)
            )

        return scenes
