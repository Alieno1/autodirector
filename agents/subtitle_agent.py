"""
subtitle_agent.py
------------------
AGENT 4 (pre-assembly): The Subtitle Sync Engineer

TWO MODES:
  PROPORTIONAL (default): proportional character-length timing. Works well
  for steady TTS cadences (espeak-ng, Google TTS).

  WHISPER (USE_WHISPER=true): runs the audio through OpenAI Whisper
  (word_timestamps=True) for real per-word timestamps. Best with expressive
  voices (ElevenLabs). Requires: pip install openai-whisper
"""

from __future__ import annotations

from config import settings
from core.exceptions import SubtitleError
from core.logger import get_logger
from models import Caption, Scene

log = get_logger(__name__)


def _chunk_words(words: list[str], chunk_size: int = 3) -> list[list[str]]:
    return [words[i : i + chunk_size] for i in range(0, len(words), chunk_size)]


def _proportional_captions(scene: Scene) -> list[Caption]:
    """Character-length proportional timing — deterministic, zero dependencies."""
    words = scene.narration.split()
    duration = scene.duration
    total_chars = sum(len(w) for w in words) or 1

    captions: list[Caption] = []
    t = 0.0
    for chunk in _chunk_words(words, chunk_size=3):
        chunk_chars = sum(len(w) for w in chunk)
        chunk_dur = duration * (chunk_chars / total_chars)
        captions.append(Caption(text=" ".join(chunk), start=round(t, 3), end=round(t + chunk_dur, 3)))
        t += chunk_dur

    if captions:
        captions[-1].end = round(duration, 3)
    return captions


def _whisper_captions(scene: Scene) -> list[Caption]:
    """Real word-level timestamps from Whisper. Requires openai-whisper."""
    try:
        import whisper  # type: ignore[import]
    except ImportError as exc:
        raise SubtitleError(
            "USE_WHISPER=true but 'openai-whisper' is not installed. Run: pip install openai-whisper"
        ) from exc

    log.debug("Scene %d: running Whisper forced alignment...", scene.id)
    model = whisper.load_model("base")
    result = model.transcribe(scene.audio_path, word_timestamps=True, language="en", verbose=False)

    word_entries = [w for seg in result.get("segments", []) for w in seg.get("words", [])]
    if not word_entries:
        log.warning("Scene %d: Whisper returned no word timestamps — falling back to proportional.", scene.id)
        return _proportional_captions(scene)

    captions: list[Caption] = []
    for i in range(0, len(word_entries), 3):
        chunk = word_entries[i : i + 3]
        captions.append(Caption(
            text=" ".join(w["word"].strip() for w in chunk),
            start=round(chunk[0]["start"], 3),
            end=round(chunk[-1]["end"], 3),
        ))
    return captions


class SubtitleAgent:
    def run(self, scenes: list[Scene]) -> list[Scene]:
        """Compute timed captions for all scenes."""
        mode = "Whisper" if settings.USE_WHISPER else "proportional"
        log.info("Aligning captions for %d scenes using %s...", len(scenes), mode)

        for scene in scenes:
            if not scene.is_voice_ready():
                raise SubtitleError(
                    f"Scene {scene.id} missing audio_path/duration — VoiceAgent must run first."
                )

            if settings.USE_WHISPER:
                try:
                    scene.captions = _whisper_captions(scene)
                except SubtitleError:
                    raise
                except Exception as exc:
                    log.warning("Scene %d: Whisper failed (%s) — falling back to proportional.", scene.id, exc)
                    scene.captions = _proportional_captions(scene)
            else:
                scene.captions = _proportional_captions(scene)

            log.debug("Scene %d: %d caption chunks.", scene.id, len(scene.captions))

        return scenes
