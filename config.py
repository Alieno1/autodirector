"""
config.py
---------
Central configuration for Auto-Director — production edition.

DESIGN:
  Uses `pydantic-settings` to validate all configuration at startup.
  This means:
    1. Bad values (e.g. VIDEO_WIDTH="hello") raise a clear error immediately,
       not a cryptic crash deep inside moviepy.
    2. All settings are typed, documented, and auto-populated from:
         a. Environment variables  (highest priority)
         b. A `.env` file in the project root  (copy from .env.example)
         c. Field defaults  (lowest priority — sensible offline fallbacks)
    3. Adding a new knob is one line; no scattered os.environ.get() calls.

USAGE:
    from config import settings

    if settings.USE_LIVE_LLM:
        ...

    settings.VIDEO_WIDTH  # → 1080
"""

from __future__ import annotations

import os
from functools import cached_property
from typing import Optional

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All runtime configuration for the Auto-Director pipeline.
    Values are read from environment variables or a .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,   # GEMINI_API_KEY and gemini_api_key both work
        extra="ignore",         # silently skip unrecognised env vars
    )

    # ── API Keys ─────────────────────────────────────────────────────────────
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API key")
    OPENROUTER_API_KEY: str = Field(default="", description="OpenRouter API key for LLM scripts")
    REPLICATE_API_TOKEN: str = Field(default="", description="Replicate API key for text-to-video")
    ELEVENLABS_API_KEY: str = Field(default="", description="ElevenLabs TTS API key")
    GOOGLE_TTS_API_KEY: str = Field(default="", description="Google Cloud TTS API key")

    # ── Mode flags (auto-derived, read-only) ──────────────────────────────────
    # These are computed in the validator below; do NOT set them in .env.

    # ── Video output settings ─────────────────────────────────────────────────
    VIDEO_WIDTH: int = Field(default=1080, ge=360, le=3840, description="Output frame width in pixels")
    VIDEO_HEIGHT: int = Field(default=1920, ge=640, le=7680, description="Output frame height in pixels")
    FPS: int = Field(default=30, ge=1, le=60, description="Output video frame rate")
    MAX_VIDEO_DURATION: int = Field(default=90, ge=10, le=600, description="Maximum video playback length in seconds")

    # ── Subtitle mode ─────────────────────────────────────────────────────────
    USE_WHISPER: bool = Field(
        default=False,
        description=(
            "Use OpenAI Whisper for real word-level timestamp alignment. "
            "Requires: pip install openai-whisper. Downloads ~150 MB model on first run."
        ),
    )

    # ── Logging ───────────────────────────────────────────────────────────────
    LOG_LEVEL: str = Field(default="INFO", description="Logging level: DEBUG | INFO | WARNING | ERROR")

    # ── Retry ─────────────────────────────────────────────────────────────────
    API_MAX_RETRIES: int = Field(default=3, ge=1, le=10, description="Max API call attempts before fallback")
    API_BASE_DELAY: float = Field(default=1.0, ge=0.1, le=60.0, description="Base retry delay in seconds (exponential backoff)")

    # ── Path configuration ────────────────────────────────────────────────────
    BASE_DIR: str = Field(default="", description="Project root directory (auto-set)")
    TEMP_DIR: str = Field(default="", description="Temp directory for intermediate files (auto-set)")
    OUTPUT_DIR: str = Field(default="", description="Output directory for final video (auto-set)")

    # ── Validators ───────────────────────────────────────────────────────────

    @field_validator("LOG_LEVEL")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        upper = v.upper()
        if upper not in valid:
            raise ValueError(f"LOG_LEVEL must be one of {valid}, got '{v}'")
        return upper

    @model_validator(mode="after")
    def _set_derived_paths(self) -> "Settings":
        """Auto-set base/temp/output dirs relative to this file's location."""
        base = os.path.dirname(os.path.abspath(__file__))
        if not self.BASE_DIR:
            self.BASE_DIR = base
        if not self.TEMP_DIR:
            self.TEMP_DIR = os.path.join(self.BASE_DIR, "temp")
        if not self.OUTPUT_DIR:
            self.OUTPUT_DIR = os.path.join(self.BASE_DIR, "output")

        os.makedirs(self.TEMP_DIR, exist_ok=True)
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
        return self

    # ── Computed properties ───────────────────────────────────────────────────

    @cached_property
    def USE_LIVE_LLM(self) -> bool:
        """True when an OpenRouter or Gemini key is present → use LLM for scene breakdown."""
        return bool(self.OPENROUTER_API_KEY or self.GEMINI_API_KEY)

    @cached_property
    def USE_LIVE_TTS(self) -> bool:
        """True when any TTS key is present → use a live voice provider."""
        return bool(self.ELEVENLABS_API_KEY or self.GOOGLE_TTS_API_KEY)

    @cached_property
    def USE_LIVE_VIDEO_GEN(self) -> bool:
        """True when a Replicate token is present → use Replicate for full video generation."""
        return bool(self.REPLICATE_API_TOKEN)

    @cached_property
    def active_mode(self) -> str:
        """Human-readable label for the current operating mode."""
        if self.USE_LIVE_LLM or self.USE_LIVE_TTS:
            providers = []
            if self.GEMINI_API_KEY:
                providers.append("Gemini")
            if self.ELEVENLABS_API_KEY:
                providers.append("ElevenLabs")
            elif self.GOOGLE_TTS_API_KEY:
                providers.append("Google TTS")
            return f"LIVE ({', '.join(providers)})"
        return "DEMO (offline)"


# ── Singleton ─────────────────────────────────────────────────────────────────
# Import this everywhere:  from config import settings
settings = Settings()
