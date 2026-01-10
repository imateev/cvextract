"""
Shared OpenAI helper utilities for adjusters.
"""

from __future__ import annotations

import json
import random
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar

try:
    # Python 3.9+
    from importlib.resources import as_file, files
except ModuleNotFoundError:
    # Python < 3.9 backport
    from importlib_resources import as_file, files  # type: ignore

T = TypeVar("T")


def get_cached_resource_path(
    resource_name: str,
    *,
    package: str = "cvextract.contracts",
    cache_filename: Optional[str] = None,
) -> Optional[Path]:
    """Return a cached filesystem path for a bundled resource, if available."""
    try:
        resource = files(package).joinpath(resource_name)

        cache_dir = Path(tempfile.gettempdir()) / "cvextract"
        cache_dir.mkdir(parents=True, exist_ok=True)

        cache_name = cache_filename or resource_name
        cache_path = cache_dir / cache_name
        if cache_path.exists():
            return cache_path

        with as_file(resource) as p:
            src = Path(p)
            if not src.exists():
                return None
            cache_path.write_bytes(src.read_bytes())

        return cache_path if cache_path.exists() else None
    except Exception:
        return None


@dataclass(frozen=True)
class RetryConfig:
    max_attempts: int = 8
    base_delay_s: float = 0.75
    max_delay_s: float = 20.0
    write_multiplier: float = 1.6
    deterministic: bool = False


def strip_markdown_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[len("```json") :]
    elif text.startswith("```"):
        text = text[len("```") :]
    if text.endswith("```"):
        text = text[: -len("```")]
    return text.strip()


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """
    Robustly extract a JSON object from model output.

    Handles:
    - pure JSON
    - fenced code blocks
    - extra commentary around JSON
    """
    if not isinstance(text, str):
        return None

    cleaned = strip_markdown_fences(text)

    try:
        obj = json.loads(cleaned)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = cleaned[start : end + 1]
    try:
        obj = json.loads(candidate)
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


class OpenAIRetry:
    def __init__(
        self,
        *,
        retry: RetryConfig,
        sleep: Callable[[float], None],
    ):
        self._retry = retry
        self._sleep = sleep

    def _get_status_code(self, exc: Exception) -> Optional[int]:
        for attr in ("status_code", "status", "http_status"):
            val = getattr(exc, attr, None)
            if isinstance(val, int):
                return val
        resp = getattr(exc, "response", None)
        if resp is not None:
            sc = getattr(resp, "status_code", None)
            if isinstance(sc, int):
                return sc
        return None

    def _get_retry_after_s(self, exc: Exception) -> Optional[float]:
        headers = getattr(exc, "headers", None)
        resp = getattr(exc, "response", None)
        if headers is None and resp is not None:
            headers = getattr(resp, "headers", None)
        if not headers:
            return None
        try:
            ra = headers.get("retry-after") or headers.get("Retry-After")
        except Exception:
            return None
        if ra is None:
            return None
        try:
            return float(ra)
        except Exception:
            return None

    def _is_transient(self, exc: Exception) -> bool:
        status = self._get_status_code(exc)
        if status == 429:
            return True
        if status is not None and 500 <= status <= 599:
            return True

        msg = str(exc).lower()
        transient_markers = (
            "timeout",
            "timed out",
            "temporarily unavailable",
            "connection reset",
            "connection aborted",
            "connection refused",
            "remote disconnected",
            "bad gateway",
            "service unavailable",
            "gateway timeout",
            "tls",
            "ssl",
        )
        return any(m in msg for m in transient_markers)

    def _sleep_with_backoff(
        self, attempt_idx: int, *, is_write: bool, exc: Exception
    ) -> None:
        retry_after = self._get_retry_after_s(exc)
        if retry_after is not None and retry_after > 0:
            self._sleep(min(self._retry.max_delay_s, retry_after))
            return

        mult = self._retry.write_multiplier if is_write else 1.0
        raw = self._retry.base_delay_s * (2**attempt_idx) * mult
        capped = min(self._retry.max_delay_s, raw)

        if self._retry.deterministic:
            delay = capped
        else:
            delay = random.random() * capped  # full jitter

        delay = max(0.25, delay)
        self._sleep(delay)

    def call(self, fn: Callable[[], T], *, is_write: bool, op_name: str) -> T:
        last_exc: Optional[Exception] = None
        for attempt in range(self._retry.max_attempts):
            try:
                return fn()
            except Exception as e:
                last_exc = e
                if not self._is_transient(e):
                    raise RuntimeError(f"{op_name} failed (non-retryable): {e}") from e
                if attempt >= self._retry.max_attempts - 1:
                    status = self._get_status_code(e)
                    raise RuntimeError(
                        f"{op_name} failed after {self._retry.max_attempts} attempts"
                        + (f" (HTTP {status})" if status else "")
                        + f": {e}"
                    ) from e
                self._sleep_with_backoff(attempt, is_write=is_write, exc=e)

        raise RuntimeError(f"{op_name} failed unexpectedly: {last_exc}")
