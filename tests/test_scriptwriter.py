"""
tests/test_scriptwriter.py
--------------------------
Unit tests for ScriptwriterAgent.
"""

import pytest
from unittest.mock import patch, MagicMock

from agents.scriptwriter_agent import ScriptwriterAgent, _offline_split, _validate_scenes_payload
from core.exceptions import ScriptwriterError
from models import Scene


STORY = (
    "Riya stared at the wedding invitation. Her hands trembled. "
    "Kabir knocked at the door. He held two plane tickets. "
    "She grabbed her coat and walked out."
)


class TestOfflineSplit:
    def test_returns_list_of_dicts(self):
        result = _offline_split(STORY)
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_each_dict_has_required_keys(self):
        for scene in _offline_split(STORY):
            assert "narration" in scene
            assert "visual_prompt" in scene
            assert "mood" in scene

    def test_max_8_scenes(self):
        long_story = ". ".join([f"Sentence {i}" for i in range(50)]) + "."
        result = _offline_split(long_story)
        assert len(result) <= 8

    def test_single_sentence_story(self):
        result = _offline_split("She walked away.")
        assert len(result) >= 1

    def test_narration_non_empty(self):
        for scene in _offline_split(STORY):
            assert scene["narration"].strip()


class TestValidateScenesPayload:
    def test_valid_payload_passes(self):
        data = {
            "scenes": [
                {"narration": "Test narration.", "visual_prompt": "A shot.", "mood": "calm"}
            ]
        }
        result = _validate_scenes_payload(data)
        assert len(result) == 1

    def test_missing_scenes_key_raises(self):
        with pytest.raises(ScriptwriterError, match="missing 'scenes'"):
            _validate_scenes_payload({"foo": "bar"})

    def test_empty_scenes_list_raises(self):
        with pytest.raises(ScriptwriterError, match="empty"):
            _validate_scenes_payload({"scenes": []})

    def test_missing_key_in_scene_raises(self):
        data = {"scenes": [{"narration": "Only narration."}]}
        with pytest.raises(ScriptwriterError, match="missing required keys"):
            _validate_scenes_payload(data)


class TestScriptwriterAgent:
    def test_demo_mode_returns_scenes(self):
        """In DEMO mode (no key), agent uses offline splitter."""
        with patch("agents.scriptwriter_agent.settings") as mock_cfg:
            mock_cfg.USE_LIVE_LLM = False
            scenes = ScriptwriterAgent().run(STORY)

        assert isinstance(scenes, list)
        assert all(isinstance(s, Scene) for s in scenes)

    def test_scenes_have_sequential_ids(self):
        with patch("agents.scriptwriter_agent.settings") as mock_cfg:
            mock_cfg.USE_LIVE_LLM = False
            scenes = ScriptwriterAgent().run(STORY)

        assert [s.id for s in scenes] == list(range(len(scenes)))

    def test_empty_story_raises(self):
        with pytest.raises(ScriptwriterError, match="empty"):
            ScriptwriterAgent().run("   ")

    def test_gemini_failure_falls_back_to_offline(self):
        """If Gemini raises, agent falls back gracefully."""
        with patch("agents.scriptwriter_agent.settings") as mock_cfg:
            mock_cfg.USE_LIVE_LLM = True
            mock_cfg.API_MAX_RETRIES = 1
            mock_cfg.API_BASE_DELAY = 0.01
            with patch("agents.scriptwriter_agent._call_gemini", side_effect=RuntimeError("API down")):
                scenes = ScriptwriterAgent().run(STORY)

        assert len(scenes) >= 1
