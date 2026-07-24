"""
tests/test_visual.py
---------------------
Unit tests for VisualAgent.
"""

import os
import pytest
from unittest.mock import patch

from agents.visual_agent import VisualAgent, _offline_image
from core.exceptions import VisualError
from models import Scene


class TestOfflineImage:
    def test_writes_png_file(self, tmp_path, bare_scene):
        out = str(tmp_path / "scene_0.png")
        with patch("agents.visual_agent.settings") as mock_cfg:
            mock_cfg.VIDEO_WIDTH = 108   # small for speed
            mock_cfg.VIDEO_HEIGHT = 192
        _offline_image(bare_scene.visual_prompt, bare_scene.mood, out)
        assert os.path.exists(out)
        assert os.path.getsize(out) > 0

    def test_unknown_mood_uses_neutral_palette(self, tmp_path):
        out = str(tmp_path / "unknown.png")
        # Should not raise even with an unknown mood
        _offline_image("A scene.", "unknown_mood", out)
        assert os.path.exists(out)


class TestVisualAgent:
    def test_populates_image_path(self, tmp_path, voiced_scene):
        with patch("agents.visual_agent.settings") as mock_cfg:
            mock_cfg.USE_LIVE_IMAGE_GEN = False
            mock_cfg.VIDEO_WIDTH = 108
            mock_cfg.VIDEO_HEIGHT = 192
            mock_cfg.TEMP_DIR = str(tmp_path)
            scenes = VisualAgent().run([voiced_scene])

        assert scenes[0].image_path is not None
        assert os.path.exists(scenes[0].image_path)

    def test_gemini_failure_falls_back_to_offline(self, tmp_path, voiced_scene):
        with patch("agents.visual_agent.settings") as mock_cfg:
            mock_cfg.USE_LIVE_IMAGE_GEN = True
            mock_cfg.VIDEO_WIDTH = 108
            mock_cfg.VIDEO_HEIGHT = 192
            mock_cfg.TEMP_DIR = str(tmp_path)
            mock_cfg.API_MAX_RETRIES = 1
            mock_cfg.API_BASE_DELAY = 0.01
            with patch("agents.visual_agent._call_gemini_image", side_effect=RuntimeError("API down")):
                scenes = VisualAgent().run([voiced_scene])

        assert scenes[0].is_visual_ready()
