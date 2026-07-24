"""
models.py
---------
Typed domain model for the Auto-Director pipeline.

Every agent reads from and writes back to a list of `Scene` objects.
Using a dataclass instead of a raw dict gives:
  - IDE autocomplete & refactoring support
  - Static analysis (mypy / pyright catch typos at dev time, not runtime)
  - A single source of truth for what data flows through the pipeline
  - Easy serialisation to JSON for logging / caching
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Optional


@dataclass
class Caption:
    """A single on-screen caption chunk with millisecond-precise timing."""

    text: str
    start: float  # seconds from scene start
    end: float    # seconds from scene start

    def duration(self) -> float:
        return max(self.end - self.start, 0.0)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Scene:
    """
    Represents one scene in the pipeline.

    Fields are added incrementally by each agent:
      ScriptwriterAgent  → id, narration, visual_prompt, mood
      VoiceAgent         → audio_path, duration
      VisualAgent        → image_path
      SubtitleAgent      → captions
    """

    id: int
    narration: str
    visual_prompt: str
    mood: str

    # Set by VoiceAgent
    audio_path: Optional[str] = None
    duration: Optional[float] = None

    # Set by VisualAgent
    image_path: Optional[str] = None

    # Set by SubtitleAgent
    captions: list[Caption] = field(default_factory=list)

    # ── Convenience helpers ──────────────────────────────────────────────────

    def is_voice_ready(self) -> bool:
        """True once VoiceAgent has populated this scene."""
        return self.audio_path is not None and self.duration is not None

    def is_visual_ready(self) -> bool:
        """True once VisualAgent has populated this scene."""
        return self.image_path is not None

    def is_render_ready(self) -> bool:
        """True once all agents have finished — safe to pass to DirectorAgent."""
        return self.is_voice_ready() and self.is_visual_ready() and bool(self.captions)

    def to_dict(self) -> dict:
        d = asdict(self)
        return d

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_dict(cls, data: dict) -> "Scene":
        # BUG FIX: use a copy + get() instead of pop() so we never silently
        # mutate the caller's dict (pop modifies the original in-place).
        data = dict(data)  # shallow copy — safe to modify now
        raw_captions = data.pop("captions", [])
        captions = [Caption(**c) for c in raw_captions]
        return cls(**data, captions=captions)
