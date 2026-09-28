"""
scriptwriter_agent.py
----------------------
AGENT 1: The Scriptwriter

Job: take a raw text story and produce a structured shot list —
a list of typed `Scene` objects, each with narration, visual_prompt, and mood.

LIVE MODE : Calls Gemini (gemini-2.5-flash) with a structured-JSON prompt.
            The API call is wrapped with retry/backoff (3 attempts by default).
DEMO MODE : A deterministic rule-based sentence splitter — no API key needed.
            Falls back to this automatically if the Gemini call fails.
"""

from __future__ import annotations

import json
import re
import requests

from config import settings
from core.exceptions import ScriptwriterError
from core.logger import get_logger
from core.retry import retry_api_call
from models import Scene

log = get_logger(__name__)


# ── Prompt ────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a professional short-drama script editor for 60-second vertical micro-dramas.
Break the given story into 4-8 filmable scenes.

Return ONLY valid JSON (no markdown fences, no preamble) in this exact shape:
{
  "scenes": [
    {
      "narration": "the exact line(s) of narration/dialogue to voice for this scene",
      "visual_prompt": "a vivid, concrete text-to-image prompt describing the shot",
      "mood": "one word: e.g. tense, romantic, joyful, ominous, calm"
    }
  ]
}
Keep narration lines short (under 25 words) so they fit a fast-paced short video.
IMPORTANT: The entire video MUST be strictly under 90 seconds long. Your total script (sum of all narrations) MUST NOT exceed 130 words. Keep it absolutely concise, or it will be chopped off.

CRITICAL LANGUAGE REQUIREMENT:
1. Match the language of the "narration" to the language of the input story (e.g., if the input is in Hindi, the narration must be in Hindi; if it is in Hinglish, the narration must be in Hinglish; if it is in English, the narration must be in English).
2. The "visual_prompt" must ALWAYS be written in English (so that image generation models can understand it).
"""

_REQUIRED_KEYS = {"narration", "visual_prompt", "mood"}


# ── Live provider ─────────────────────────────────────────────────────────────

@retry_api_call(
    max_attempts=settings.API_MAX_RETRIES,
    base_delay=settings.API_BASE_DELAY,
)
def _call_openrouter(story_text: str) -> dict:
    """Real call to the OpenRouter API. Retried automatically on transient errors."""
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://localhost:8501", # Required by OpenRouter
        "X-Title": "Auto-Director", # Required by OpenRouter
    }
    payload = {
        "model": "meta-llama/llama-3.1-8b-instruct",
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": story_text}
        ],
        "temperature": 0.7,
        "response_format": {"type": "json_object"}
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    raw_text = data["choices"][0]["message"]["content"]
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        # Fallback to manual extraction if the model wraps output in markdown code blocks
        import re
        json_match = re.search(r"```json\s*(.*?)\s*```", raw_text, flags=re.DOTALL)
        if json_match:
            return json.loads(json_match.group(1))
        raise ScriptwriterError(f"OpenRouter did not return valid JSON: {raw_text}")


@retry_api_call(
    max_attempts=settings.API_MAX_RETRIES,
    base_delay=settings.API_BASE_DELAY,
)
def _call_gemini(story_text: str) -> dict:
    import requests
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"gemini-flash-latest:generateContent?key={settings.GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"parts": [{"text": _SYSTEM_PROMPT + "\n\nSTORY:\n" + story_text}]}],
        "generationConfig": {"temperature": 0.7, "response_mime_type": "application/json"},
    }
    resp = requests.post(url, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
    return json.loads(raw_text)




def _validate_scenes_payload(data: dict) -> list[dict]:
    """
    Validate the JSON response from Gemini before trusting it.
    Raises ScriptwriterError if the response is malformed.
    """
    if "scenes" not in data or not isinstance(data["scenes"], list):
        raise ScriptwriterError(f"Gemini response missing 'scenes' list. Got keys: {list(data.keys())}")

    scenes = data["scenes"]
    if not scenes:
        raise ScriptwriterError("Gemini returned an empty scenes list.")

    for i, s in enumerate(scenes):
        missing = _REQUIRED_KEYS - set(s.keys())
        if missing:
            raise ScriptwriterError(
                f"Scene {i} is missing required keys: {missing}. Got: {list(s.keys())}"
            )

    return scenes


# ── Offline fallback ──────────────────────────────────────────────────────────

def _offline_split(story_text: str) -> list[dict]:
    """
    Deterministic fallback: splits the story into sentence-groups and derives
    a naive visual prompt from each. No network calls.
    """
    sentences = re.split(r"(?<=[.!?])\s+", story_text.strip())
    sentences = [s.strip() for s in sentences if s.strip()]

    group_size = max(1, len(sentences) // 6)
    scenes: list[dict] = []
    for i in range(0, len(sentences), group_size):
        chunk = " ".join(sentences[i : i + group_size])
        scenes.append(
            {
                "narration": chunk,
                "visual_prompt": f"Cinematic vertical shot illustrating: {chunk[:80]}",
                "mood": "neutral",
            }
        )
        if len(scenes) >= 8:
            break
    return scenes


# ── Agent ─────────────────────────────────────────────────────────────────────

class ScriptwriterAgent:
    def run(self, story_text: str) -> list[Scene]:
        """
        Parse a story into a list of typed Scene objects.

        Args:
            story_text: Raw story text to be broken into scenes.

        Returns:
            A list of Scene objects ready for VoiceAgent.

        Raises:
            ScriptwriterError: If no scenes could be produced at all.
        """
        if not story_text.strip():
            raise ScriptwriterError("story_text is empty — nothing to process.")

        raw_scenes: list[dict]

        if settings.USE_LIVE_LLM:
            try:
                if settings.OPENROUTER_API_KEY:
                    log.info("Calling OpenRouter for scene breakdown...")
                    data = _call_openrouter(story_text)
                else:
                    log.info("Calling Gemini for scene breakdown...")
                    data = _call_gemini(story_text)
                
                raw_scenes = _validate_scenes_payload(data)
                log.info("LLM returned %d scenes.", len(raw_scenes))
            except Exception as exc:
                log.warning(
                    "LLM call failed (%s: %s) — falling back to offline splitter.",
                    type(exc).__name__,
                    exc,
                )
                raw_scenes = _offline_split(story_text)
        else:
            log.info("No LLM key — using offline rule-based splitter.")
            raw_scenes = _offline_split(story_text)

        if not raw_scenes:
            raise ScriptwriterError("Scene list is empty after processing. Cannot continue.")

        scenes = [
            Scene(
                id=idx,
                narration=s["narration"],
                visual_prompt=s["visual_prompt"],
                mood=s.get("mood", "neutral"),
            )
            for idx, s in enumerate(raw_scenes)
        ]

        log.debug(
            "Scenes produced: %s",
            [f"#{s.id} ({s.mood})" for s in scenes],
        )
        return scenes
