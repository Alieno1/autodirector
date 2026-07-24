"""
tests/test_director.py
-----------------------
Unit tests for DirectorAgent.

We mock moviepy entirely to avoid needing a real ffmpeg install in unit tests.
The integration test (test_pipeline.py) covers the real render path.
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from agents.director_agent import DirectorAgent, _ken_burns_clip, _resolve_font
from core.exceptions import DirectorError
from models import Scene


class TestResolveFont:
    def test_returns_existing_path(self, tmp_path):
        fake_font = tmp_path / "fake.ttf"
        fake_font.write_bytes(b"")  # just needs to exist
        with patch("agents.director_agent._DEFAULT_ENGLISH_FONTS", [str(fake_font)]):
            result = _resolve_font("English text")
        assert result == str(fake_font)

    def test_raises_if_no_font_found(self):
        with patch("agents.director_agent._DEFAULT_ENGLISH_FONTS", ["/nonexistent/font.ttf"]):
            with pytest.raises(DirectorError, match="No suitable bold font"):
                _resolve_font("English text")


class TestDirectorAgent:
    def test_raises_if_scene_not_render_ready(self, voiced_scene):
        """Director should raise if image_path or captions are missing."""
        # voiced_scene has audio+duration but no image_path or captions
        with pytest.raises(DirectorError, match="not render-ready"):
            DirectorAgent().run([voiced_scene], "out.mp4")

    def test_returns_output_path(self, tmp_path, sample_scenes):
        """Mock moviepy so we can test the path-building logic without ffmpeg."""
        mock_clip = MagicMock()
        mock_clip.w = 1080
        mock_clip.h = 1920
        mock_clip.resized.return_value = mock_clip
        mock_clip.with_duration.return_value = mock_clip
        mock_clip.with_position.return_value = mock_clip
        mock_clip.with_start.return_value = mock_clip
        mock_clip.with_audio.return_value = mock_clip

        mock_text_clip = MagicMock()
        mock_text_clip.with_start.return_value = mock_text_clip
        mock_text_clip.with_duration.return_value = mock_text_clip
        mock_text_clip.with_position.return_value = mock_text_clip
        mock_text_clip.duration.return_value = 0.5

        fake_font = tmp_path / "fake.ttf"
        fake_font.write_bytes(b"")

        with patch("agents.director_agent._DEFAULT_ENGLISH_FONTS", [str(fake_font)]):
            with patch("agents.director_agent.settings") as mock_cfg:
                mock_cfg.VIDEO_WIDTH = 1080
                mock_cfg.VIDEO_HEIGHT = 1920
                mock_cfg.FPS = 30
                mock_cfg.OUTPUT_DIR = str(tmp_path)
                with patch("moviepy.ImageClip", return_value=mock_clip):
                    with patch("moviepy.TextClip", return_value=mock_text_clip):
                        with patch("moviepy.AudioFileClip", return_value=mock_clip):
                            with patch("moviepy.CompositeVideoClip", return_value=mock_clip):
                                with patch("moviepy.concatenate_videoclips", return_value=mock_clip):
                                    result = DirectorAgent().run(sample_scenes, "test_out.mp4")

        assert result.endswith("test_out.mp4")
