"""
core/exceptions.py
-------------------
Custom exception hierarchy for Auto-Director.

Using typed exceptions instead of bare `Exception` lets callers decide exactly
which failure they can recover from vs. which should abort the pipeline. Every
agent raises its own subclass so tracebacks immediately tell you which stage failed.
"""


class AutoDirectorError(Exception):
    """Base class for all Auto-Director pipeline errors."""


class ScriptwriterError(AutoDirectorError):
    """Raised when ScriptwriterAgent cannot produce a valid scene list."""


class VoiceError(AutoDirectorError):
    """Raised when VoiceAgent cannot synthesise audio for a scene."""


class VisualError(AutoDirectorError):
    """Raised when VisualAgent cannot produce an image for a scene."""


class SubtitleError(AutoDirectorError):
    """Raised when SubtitleAgent cannot produce captions for a scene."""


class DirectorError(AutoDirectorError):
    """Raised when DirectorAgent cannot assemble or write the final video."""


class ConfigurationError(AutoDirectorError):
    """Raised on invalid or incompatible configuration at startup."""
