"""
core/retry.py
-------------
Retry / exponential-backoff decorator for external API calls.

Uses `tenacity` under the hood — the most battle-tested retry library for Python.

Usage::

    from core.retry import retry_api_call

    @retry_api_call()
    def _call_elevenlabs(text: str, out_path: str) -> None:
        ...

The decorator logs each attempt and the delay before the next one.
After `max_attempts` failures the final exception is re-raised so the caller's
`except` block can still fall back to offline mode.
"""

import functools
import logging
from typing import Callable, Type

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
    after_log,
)

_log = logging.getLogger("autodirector.retry")


def _should_retry_exception(exc: Exception) -> bool:
    """Do not retry on non-transient HTTP 4xx status codes (e.g. 401 Unauthorized, 402 Payment Required)."""
    import requests
    if isinstance(exc, requests.exceptions.HTTPError) and exc.response is not None:
        status = exc.response.status_code
        if 400 <= status < 500 and status not in (408, 429):
            return False
    return True


def retry_api_call(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    reraise: bool = True,
    exceptions: tuple[Type[Exception], ...] = (Exception,),
) -> Callable:
    """
    Decorator factory that wraps a function with retry logic.

    Args:
        max_attempts: Total number of tries before giving up.
        base_delay:   Initial wait in seconds (doubled each retry).
        max_delay:    Cap on wait time between retries.
        reraise:      If True (default), re-raise the last exception after
                      all attempts are exhausted so callers can fall back.
        exceptions:   Exception types to retry on. Default: any Exception.

    Example::

        @retry_api_call(max_attempts=3, base_delay=1.0)
        def _call_gemini(story: str) -> dict:
            ...
    """
    from tenacity import retry_if_exception

    def decorator(func: Callable) -> Callable:
        def predicate(exc: Exception) -> bool:
            return isinstance(exc, exceptions) and _should_retry_exception(exc)

        retried = retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=base_delay, max=max_delay),
            retry=retry_if_exception(predicate),
            before_sleep=before_sleep_log(_log, logging.WARNING),
            after=after_log(_log, logging.DEBUG),
            reraise=reraise,
        )(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return retried(*args, **kwargs)

        return wrapper

    return decorator
