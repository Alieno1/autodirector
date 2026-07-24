"""
tests/test_subtitle_render.py
-------------------------------
Unit test to verify subtitle PNG rendering, English/Hindi language font resolution, and MoviePy 2.x transparent overlay.
"""

import os
from PIL import Image
from moviepy import ImageClip

from agents.director_agent import _caption_clip, _render_caption_png, _resolve_font, _clean_caption_text
from models import Caption


def test_clean_caption_text():
    raw = "**All the best** for your journey — stay 'strong'..."
    cleaned = _clean_caption_text(raw)
    assert "*" not in cleaned
    assert "All the best for your journey - stay 'strong'..." == cleaned


def test_resolve_font_english_and_hindi():
    font_en = _resolve_font("Hello world")
    font_hi = _resolve_font("नमस्ते दुनिया")

    assert os.path.exists(font_en)
    assert os.path.exists(font_hi)
    assert "DejaVu" in font_en or "Liberation" in font_en or "NotoSans" in font_en
    assert "Devanagari" in font_hi or "Noto" in font_hi


def test_render_caption_png_creates_non_empty_rgba_image(tmp_path):
    font_path = _resolve_font("Testing subtitle pill rendering")
    out_png = str(tmp_path / "caption_test.png")

    _render_caption_png("Testing subtitle pill rendering", out_png, font_path)

    assert os.path.exists(out_png)
    img = Image.open(out_png)
    assert img.mode == "RGBA"
    assert img.width > 0 and img.height > 0


def test_caption_clip_has_alpha_mask(tmp_path):
    font_path = _resolve_font("Alpha Mask Test")
    caption = Caption(text="Alpha Mask Test", start=0.0, end=2.0)

    clip = _caption_clip(caption, font_path, scene_id=99, caption_idx=0)

    assert isinstance(clip, ImageClip)
    assert clip.mask is not None
