"""
core/logger.py
--------------
Centralised logger factory for Auto-Director.

Design goals:
  - Structured output: every log record includes level, timestamp, logger name,
    and the message — easy to pipe into Datadog / CloudWatch / Loki.
  - A single `get_logger(name)` call in each module; no boilerplate.
  - `--verbose` (DEBUG) vs. default (INFO) controlled by a single env var or
    CLI flag — not scattered across files.
  - No external logging libraries required; built on Python stdlib `logging`.
"""

import logging
import sys


# ── Module-level root logger ─────────────────────────────────────────────────

_CONFIGURED = False


def configure_logging(level: str = "INFO") -> None:
    """
    Configure (or reconfigure) the root 'autodirector' logger.

    Safe to call multiple times — subsequent calls update the log level on
    both the root logger and all its handlers, so --verbose works even if
    get_logger() was already called during module import.
    """
    global _CONFIGURED

    numeric = getattr(logging, level.upper(), logging.INFO)
    root = logging.getLogger("autodirector")

    if not _CONFIGURED:
        # First call: attach a handler
        handler = logging.StreamHandler(sys.stderr)
        fmt = logging.Formatter(
            fmt="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
        handler.setFormatter(fmt)
        root.addHandler(handler)
        root.propagate = False
        _CONFIGURED = True

    # BUG FIX: always update the level so --verbose works even after the first
    # configure_logging() call that happened implicitly via get_logger() at
    # module import time.
    root.setLevel(numeric)
    for handler in root.handlers:
        handler.setLevel(numeric)


def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger under the 'autodirector' namespace.

    Usage in any module::

        from core.logger import get_logger
        log = get_logger(__name__)
        log.info("Processing scene %d", scene.id)
    """
    # Ensure a base configuration exists even if configure_logging wasn't called
    # (e.g., in tests or when imported as a library).
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(f"autodirector.{name}")
