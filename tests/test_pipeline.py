"""
tests/test_pipeline.py
-----------------------
End-to-end smoke test: runs the FULL pipeline in DEMO mode.

This test is intentionally slow (~10-30s) because it calls real espeak-ng,
PIL, and moviepy. It proves the entire orchestration works without any API keys.

Mark with `-m slow` and skip in fast CI with: pytest -m "not slow"
"""

import os
import pytest

# Require system deps — skip gracefully if missing
pytest.importorskip("moviepy", reason="moviepy not installed")

import subprocess
result = subprocess.run(["which", "espeak-ng"], capture_output=True)
if result.returncode != 0:
    pytest.skip("espeak-ng not installed — skipping end-to-end test", allow_module_level=True)


@pytest.mark.slow
def test_full_demo_pipeline(tmp_path):
    """
    Run the complete pipeline in DEMO mode with a minimal 2-sentence story.
    Verifies that a non-empty MP4 is written to the output directory.
    """
    from unittest.mock import patch

    story = "She walked into the room. He turned around slowly."

    with patch("config.settings") as mock_settings:
        mock_settings.USE_LIVE_LLM = False
        mock_settings.USE_LIVE_TTS = False
        mock_settings.USE_LIVE_IMAGE_GEN = False
        mock_settings.USE_WHISPER = False
        mock_settings.ELEVENLABS_API_KEY = ""
        mock_settings.VIDEO_WIDTH = 108    # tiny frame for speed
        mock_settings.VIDEO_HEIGHT = 192
        mock_settings.FPS = 5
        mock_settings.TEMP_DIR = str(tmp_path / "temp")
        mock_settings.OUTPUT_DIR = str(tmp_path / "output")
        mock_settings.API_MAX_RETRIES = 1
        mock_settings.API_BASE_DELAY = 0.01
        os.makedirs(mock_settings.TEMP_DIR, exist_ok=True)
        os.makedirs(mock_settings.OUTPUT_DIR, exist_ok=True)

        from agents.scriptwriter_agent import ScriptwriterAgent
        from agents.voice_agent import VoiceAgent
        from agents.visual_agent import VisualAgent
        from agents.subtitle_agent import SubtitleAgent
        from agents.director_agent import DirectorAgent

        scenes = ScriptwriterAgent().run(story)
        assert len(scenes) >= 1

        scenes = VoiceAgent().run(scenes)
        assert all(s.is_voice_ready() for s in scenes)

        scenes = VisualAgent().run(scenes)
        assert all(s.is_visual_ready() for s in scenes)

        scenes = SubtitleAgent().run(scenes)
        assert all(s.captions for s in scenes)

        out_path = DirectorAgent().run(scenes, "smoke_test.mp4")

    assert os.path.exists(out_path), f"Expected output file at: {out_path}"
    assert os.path.getsize(out_path) > 1000, "Output MP4 is suspiciously small"
