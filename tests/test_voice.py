"""
tests/test_voice.py
-------------------
Unit tests for VoiceAgent.
"""

import os
import wave
import struct
import pytest
from unittest.mock import patch, MagicMock

from agents.voice_agent import VoiceAgent, _offline_tts
from core.exceptions import VoiceError
from models import Scene


def make_wav(path: str, duration_s: float = 1.0, sample_rate: int = 44100) -> None:
    """Write a silent WAV file to `path`."""
    n_frames = int(duration_s * sample_rate)
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(struct.pack("<" + "h" * n_frames, *([0] * n_frames)))


class TestOfflineTTS:
    def test_calls_espeak(self, tmp_path):
        out = str(tmp_path / "test.wav")
        with patch("agents.voice_agent._gtts_fallback", side_effect=RuntimeError("no gTTS")):
            with patch("agents.voice_agent.subprocess.run") as mock_run:
                # Simulate espeak actually writing the file
                mock_run.return_value = MagicMock(returncode=0)
                make_wav(out)          # create the file so the existence check passes
                _offline_tts("Hello world.", out)
            mock_run.assert_called_once()
            assert "espeak-ng" in mock_run.call_args[0][0]

    def test_raises_if_no_output_file(self, tmp_path):
        out = str(tmp_path / "missing.wav")
        with patch("agents.voice_agent._gtts_fallback", side_effect=RuntimeError("no gTTS")):
            with patch("agents.voice_agent.subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                # Do NOT create the file → should raise VoiceError
                with pytest.raises(VoiceError, match="produced no output file"):
                    _offline_tts("Hello.", out)


class TestVoiceAgent:
    def test_populates_audio_path_and_duration(self, tmp_path, bare_scene):
        """Agent should set audio_path and duration on each scene."""
        wav_path = str(tmp_path / "voice_0.wav")
        make_wav(wav_path, duration_s=2.0)

        with patch("agents.voice_agent.settings") as mock_cfg:
            mock_cfg.USE_LIVE_TTS = False
            mock_cfg.ELEVENLABS_API_KEY = ""
            mock_cfg.TEMP_DIR = str(tmp_path)
            with patch("agents.voice_agent._offline_tts") as mock_tts:
                # Simulate espeak writing the file
                mock_tts.side_effect = lambda text, path: make_wav(path, 1.0)
                scenes = VoiceAgent().run([bare_scene])

        assert scenes[0].audio_path is not None
        assert os.path.exists(scenes[0].audio_path)
        assert scenes[0].duration > 0

    def test_elevenlabs_failure_falls_back(self, tmp_path, bare_scene):
        with patch("agents.voice_agent.settings") as mock_cfg:
            mock_cfg.USE_LIVE_TTS = True
            mock_cfg.ELEVENLABS_API_KEY = "fake-key"
            mock_cfg.TEMP_DIR = str(tmp_path)
            mock_cfg.API_MAX_RETRIES = 1
            mock_cfg.API_BASE_DELAY = 0.01
            with patch("agents.voice_agent._call_elevenlabs", side_effect=RuntimeError("rate limit")):
                with patch("agents.voice_agent._offline_tts") as mock_tts:
                    mock_tts.side_effect = lambda text, path: make_wav(path, 1.0)
                    scenes = VoiceAgent().run([bare_scene])

        assert scenes[0].is_voice_ready()
