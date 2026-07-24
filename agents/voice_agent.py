"""
voice_agent.py
--------------
AGENT 2: The Voice Actor

Job: turn each scene's narration text into a .wav audio file and record
its exact duration — everything downstream relies on these real durations
for sync (captions, Ken Burns timing, final video length).

LIVE MODE : ElevenLabs (natural, expressive voices).
            API call is retried with exponential backoff.
DEMO MODE : espeak-ng, a fast offline TTS engine. Robotic but deterministic.

PERFORMANCE: All scenes are processed concurrently via ThreadPoolExecutor.
             On a 6-scene story this is ~6× faster than sequential.
"""

from __future__ import annotations

import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

from config import settings
from core.exceptions import VoiceError
from core.logger import get_logger
from core.retry import retry_api_call
from models import Scene

log = get_logger(__name__)


# ── Live provider: ElevenLabs ─────────────────────────────────────────────────

@retry_api_call(
    max_attempts=settings.API_MAX_RETRIES,
    base_delay=settings.API_BASE_DELAY,
)
def _call_elevenlabs(text: str, out_path: str) -> None:
    import requests

    voice_id = "21m00Tcm4TlvDq8ikWAM"  # default ElevenLabs voice
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {"text": text, "model_id": "eleven_multilingual_v2"}

    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()

    with open(out_path, "wb") as f:
        f.write(resp.content)


def _gtts_fallback(text: str, out_path: str) -> None:
    """Natural, smooth Google Text-To-Speech fallback for Hindi and English."""
    from gtts import gTTS
    import re

    # Detect Devanagari script for Hindi
    is_hindi = bool(re.search(r"[\u0900-\u097F]", text))
    lang = "hi" if is_hindi else "en"
    
    mp3_path = out_path.replace(".wav", ".mp3")
    tts = gTTS(text=text, lang=lang, slow=False)
    tts.save(mp3_path)

    # Convert mp3 to wav for consistency with moviepy using ffmpeg or clip
    import subprocess
    subprocess.run(
        ["ffmpeg", "-y", "-i", mp3_path, out_path],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if os.path.exists(mp3_path):
        try:
            os.remove(mp3_path)
        except OSError:
            pass


def _offline_tts(text: str, out_path: str) -> None:
    """Try gTTS first for natural voice, fall back to espeak-ng if offline."""
    try:
        _gtts_fallback(text, out_path)
    except Exception as exc:
        log.warning("gTTS failed (%s) — falling back to espeak-ng.", exc)
        subprocess.run(
            ["espeak-ng", "-s", "165", "-w", out_path, text],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if not os.path.exists(out_path):
            raise VoiceError(f"TTS produced no output file at: {out_path}")


# ── Per-scene worker ──────────────────────────────────────────────────────────

def _process_scene(scene: Scene) -> Scene:
    """
    Synthesise audio for a single scene and measure its duration.
    Called concurrently from the ThreadPoolExecutor.

    Mutates `scene` in-place and returns it.
    Raises VoiceError on unrecoverable failure.
    """
    # Import here — moviepy is heavy and only needed during actual processing
    from moviepy import AudioFileClip

    out_path = os.path.join(settings.TEMP_DIR, f"voice_{scene.id}.wav")
    text = scene.narration

    if settings.USE_LIVE_TTS and settings.ELEVENLABS_API_KEY:
        try:
            log.debug("Scene %d: calling ElevenLabs TTS.", scene.id)
            _call_elevenlabs(text, out_path)
        except Exception as exc:
            log.warning(
                "Scene %d: ElevenLabs failed (%s) — falling back to offline TTS (gTTS/espeak).",
                scene.id,
                exc,
            )
            _offline_tts(text, out_path)
    else:
        log.debug("Scene %d: using espeak-ng (offline TTS).", scene.id)
        _offline_tts(text, out_path)

    # Measure exact duration from the actual waveform
    clip: Optional[AudioFileClip] = None
    try:
        clip = AudioFileClip(out_path)
        scene.audio_path = out_path
        scene.duration = clip.duration
        log.debug("Scene %d: audio duration = %.2fs.", scene.id, scene.duration)
    except Exception as exc:
        raise VoiceError(f"Scene {scene.id}: could not read audio duration from '{out_path}': {exc}") from exc
    finally:
        if clip is not None:
            clip.close()

    return scene


# ── Agent ─────────────────────────────────────────────────────────────────────

class VoiceAgent:
    def run(self, scenes: list[Scene]) -> list[Scene]:
        """
        Synthesise narration audio for all scenes concurrently.

        Args:
            scenes: Scene list from ScriptwriterAgent.

        Returns:
            The same list with `audio_path` and `duration` populated on each scene.

        Raises:
            VoiceError: If any scene fails and cannot fall back.
        """
        log.info("Synthesising audio for %d scenes (parallel)...", len(scenes))

        # Use a thread pool — safe because espeak-ng/ElevenLabs are I/O-bound
        # and ThreadPoolExecutor plays well with moviepy's ffmpeg subprocesses.
        max_workers = min(len(scenes), 4)  # cap at 4 to avoid rate-limiting
        errors: list[str] = []

        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="voice") as pool:
            futures = {pool.submit(_process_scene, scene): scene for scene in scenes}
            for future in as_completed(futures):
                scene = futures[future]
                try:
                    future.result()
                    log.info("Scene %d: audio ready (%.2fs).", scene.id, scene.duration)
                except Exception as exc:
                    errors.append(f"Scene {scene.id}: {exc}")
                    log.error("Scene %d: audio synthesis FAILED — %s", scene.id, exc)

        if errors:
            raise VoiceError(
                f"{len(errors)} scene(s) failed audio synthesis:\n" + "\n".join(errors)
            )

        return scenes
