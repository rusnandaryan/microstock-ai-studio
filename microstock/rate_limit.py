"""Rate-limit aware retry helpers (exponential backoff + full jitter)."""
from __future__ import annotations

import asyncio
import random
import re
import time
from typing import Any, Awaitable, Callable, Optional, TypeVar

from . import config

T = TypeVar("T")

RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class GenerationError(RuntimeError):
    """Raised when a call fails permanently (non-retryable or retries exhausted)."""


class TransientError(RuntimeError):
    """Raise for recoverable model hiccups (empty output, malformed JSON, no image)."""


def _status_code(exc: BaseException) -> Optional[int]:
    """Extract an HTTP status code from SDK / httpx exceptions, if available."""
    for attr in ("code", "status_code", "status"):
        val = getattr(exc, attr, None)
        if isinstance(val, int):
            return val
    resp = getattr(exc, "response", None)
    val = getattr(resp, "status_code", None)
    if isinstance(val, int):
        return val
    m = re.search(r"\b(408|429|500|502|503|504)\b", str(exc))
    return int(m.group(1)) if m else None


def is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, TransientError):
        return True
    code = _status_code(exc)
    if code in RETRYABLE_STATUS:
        return True
    text = str(exc).upper()
    # Do not retry hard quota limits (billing)
    if "QUOTA" in text and "BILLING" in text:
        return False
        
    if any(t in text for t in ("RESOURCE_EXHAUSTED", "RATE LIMIT", "UNAVAILABLE", "DEADLINE")):
        return True
    # Network-level hiccups (httpx.ConnectError, ReadTimeout, ...)
    return type(exc).__name__ in {
        "ConnectError", "ReadTimeout", "WriteTimeout", "PoolTimeout",
        "RemoteProtocolError", "ConnectTimeout", "TimeoutException",
    }


def _retry_after(exc: BaseException) -> Optional[float]:
    """Honor server-provided retry hints (Retry-After header or 'retry in Xs')."""
    resp = getattr(exc, "response", None)
    headers = getattr(resp, "headers", None)
    if headers:
        try:
            ra = headers.get("retry-after")
            if ra:
                return float(ra)
        except Exception:
            pass
    m = re.search(r"retry (?:in|after) ([\d.]+)\s*s", str(exc), re.IGNORECASE)
    return float(m.group(1)) if m else None


def backoff_delay(attempt: int, exc: Optional[BaseException] = None) -> float:
    hinted = _retry_after(exc) if exc else None
    if hinted:
        return min(hinted + random.uniform(0, 1), config.MAX_BACKOFF_SECONDS)
    ceiling = min(config.BASE_BACKOFF_SECONDS * (2 ** attempt), config.MAX_BACKOFF_SECONDS)
    return random.uniform(ceiling / 2, ceiling)  # "equal jitter"


def retry_sync(fn: Callable[[], T], *, label: str = "request",
               on_retry: Optional[Callable[[str], None]] = None) -> T:
    """Run a blocking callable with retries."""
    last: Optional[BaseException] = None
    for attempt in range(config.MAX_RETRIES + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt >= config.MAX_RETRIES or not is_retryable(exc):
                break
            delay = backoff_delay(attempt, exc)
            if on_retry:
                on_retry(f"{label}: {_short(exc)} — retrying in {delay:.1f}s "
                         f"(attempt {attempt + 2}/{config.MAX_RETRIES + 1})")
            time.sleep(delay)
    raise GenerationError(f"{label} failed: {_short(last)}") from last


async def retry_async(fn: Callable[[], Awaitable[T]], *, label: str = "request",
                      on_retry: Optional[Callable[[str], Any]] = None) -> T:
    """Await a coroutine factory with retries (non-blocking sleeps)."""
    last: Optional[BaseException] = None
    for attempt in range(config.MAX_RETRIES + 1):
        try:
            return await fn()
        except Exception as exc:  # noqa: BLE001
            last = exc
            if attempt >= config.MAX_RETRIES or not is_retryable(exc):
                break
            delay = backoff_delay(attempt, exc)
            if on_retry:
                on_retry(f"{label}: {_short(exc)} — retrying in {delay:.1f}s "
                         f"(attempt {attempt + 2}/{config.MAX_RETRIES + 1})")
            await asyncio.sleep(delay)
    raise GenerationError(f"{label} failed: {_short(last)}") from last


def _short(exc: Optional[BaseException], limit: int = 220) -> str:
    if exc is None:
        return "unknown error"
    msg = f"{type(exc).__name__}: {exc}"
    return msg if len(msg) <= limit else msg[: limit - 1] + "…"
