"""
tests/conftest.py
-----------------
Shared fixtures for all Auto-Director tests.
"""

import os
import pytest

from models import Caption, Scene


# ── Scene fixtures ────────────────────────────────────────────────────────────

@pytest.fixture()
def bare_scene() -> Scene:
    """A freshly-created scene — as produced by ScriptwriterAgent."""
    return Scene(
        id=0,
        narration="She stared at the invitation.",
        visual_prompt="Close-up of trembling hands holding a wedding card.",
        mood="tense",
    )


@pytest.fixture()
def voiced_scene(bare_scene, tmp_path) -> Scene:
    """A scene with a real (silent) WAV file so VoiceAgent output is simulated."""
    import wave, struct

    wav_path = str(tmp_path / "voice_0.wav")
    # Write a 1-second silent WAV (16-bit, 44100 Hz, mono)
    with wave.open(wav_path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(struct.pack("<" + "h" * 44100, *([0] * 44100)))

    bare_scene.audio_path = wav_path
    bare_scene.duration = 1.0
    return bare_scene


@pytest.fixture()
def captioned_scene(voiced_scene) -> Scene:
    """A fully-captioned scene."""
    voiced_scene.captions = [
        Caption(text="SHE STARED AT", start=0.0, end=0.5),
        Caption(text="THE INVITATION", start=0.5, end=1.0),
    ]
    return voiced_scene


@pytest.fixture()
def render_ready_scene(captioned_scene, tmp_path) -> Scene:
    """A render-ready scene with a small placeholder PNG."""
    from PIL import Image

    img_path = str(tmp_path / "scene_0.png")
    Image.new("RGB", (1080, 1920), color=(40, 10, 10)).save(img_path)
    captioned_scene.image_path = img_path
    return captioned_scene


@pytest.fixture()
def sample_scenes(render_ready_scene) -> list[Scene]:
    """A single-element scene list (enough to test the Director)."""
    return [render_ready_scene]
