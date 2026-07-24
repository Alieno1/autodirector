"""
tests/test_subtitle.py
-----------------------
Unit tests for SubtitleAgent.
"""

import pytest

from agents.subtitle_agent import SubtitleAgent, _proportional_captions, _chunk_words
from core.exceptions import SubtitleError
from models import Caption, Scene


class TestChunkWords:
    def test_groups_correctly(self):
        words = ["a", "b", "c", "d", "e"]
        chunks = _chunk_words(words, chunk_size=3)
        assert chunks == [["a", "b", "c"], ["d", "e"]]

    def test_single_word(self):
        assert _chunk_words(["hello"], chunk_size=3) == [["hello"]]

    def test_empty(self):
        assert _chunk_words([], chunk_size=3) == []


class TestProportionalCaptions:
    def test_returns_caption_objects(self, voiced_scene):
        captions = _proportional_captions(voiced_scene)
        assert all(isinstance(c, Caption) for c in captions)

    def test_last_caption_ends_at_duration(self, voiced_scene):
        captions = _proportional_captions(voiced_scene)
        assert captions[-1].end == pytest.approx(voiced_scene.duration, abs=0.001)

    def test_no_overlap_between_chunks(self, voiced_scene):
        captions = _proportional_captions(voiced_scene)
        for i in range(len(captions) - 1):
            assert captions[i].end <= captions[i + 1].start + 0.001

    def test_non_empty_text(self, voiced_scene):
        for cap in _proportional_captions(voiced_scene):
            assert cap.text.strip()

    def test_single_word_narration(self, voiced_scene):
        voiced_scene.narration = "Go."
        captions = _proportional_captions(voiced_scene)
        assert len(captions) == 1
        assert captions[0].end == pytest.approx(voiced_scene.duration, abs=0.001)


class TestSubtitleAgent:
    def test_populates_captions(self, voiced_scene):
        scenes = SubtitleAgent().run([voiced_scene])
        assert len(scenes[0].captions) >= 1

    def test_raises_if_voice_not_ready(self, bare_scene):
        with pytest.raises(SubtitleError, match="missing audio_path"):
            SubtitleAgent().run([bare_scene])

    def test_captions_are_typed(self, voiced_scene):
        scenes = SubtitleAgent().run([voiced_scene])
        for cap in scenes[0].captions:
            assert isinstance(cap, Caption)
            assert isinstance(cap.start, float)
            assert isinstance(cap.end, float)
