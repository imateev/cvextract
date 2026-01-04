"""
OpenAI-based job-specific adjuster.

Adjusts CV data based on a specific job description using OpenAI.

Improvements included:
- Centralized retry/backoff with jitter for 429/5xx/transient network errors
- Honors Retry-After when present
- Removes stacked retry layers (SDK max_retries + custom loop) to avoid retry storms
- Safer JSON extraction from model output (handles fenced blocks and extra text)
- Better HTML cleaning and length limiting for fetched job descriptions
- Prompt template key fallback (typo + corrected name)
- Test seams: injectable sleep + deterministic jitter option
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

try:
    # Python 3.9+
    from importlib.resources import files, as_file
except ModuleNotFoundError:
    # Python < 3.9 backport
    from importlib_resources import files, as_file  # type: ignore

from .base import CVAdjuster
from ..shared import format_prompt
from ..verifiers import get_verifier

LOG = logging.getLogger("cvextract")

T = TypeVar("T")


# CV schema cache (bundled-safe)
_CV_SCHEMA: Optional[Dict[str, Any]] = None


def _get_cv_schema_path() -> Optional[Path]:
    """Get path to CV schema, handling bundled executables (PyInstaller)."""
    try:
        schema_resource = files("cvextract.contracts").joinpath("cv_schema.json")

        # Cache to a stable location so returning Path is safe even after `as_file` closes.
        cache_dir = Path(tempfile.gettempdir()) / "cvextract"
        cache_dir.mkdir(parents=True, exist_ok=True)

        cache_path = cache_dir / "cv_schema.json"
        if cache_path.exists():
            return cache_path

        with as_file(schema_resource) as p:
            src = Path(p)
            if not src.exists():
                return None
            cache_path.write_bytes(src.read_bytes())

        return cache_path if cache_path.exists() else None
    except Exception:
        return None


_SCHEMA_PATH = _get_cv_schema_path()


def _load_cv_schema() -> Optional[Dict[str, Any]]:
    """Load the CV schema from file (cached)."""
    global _CV_SCHEMA
    if _CV_SCHEMA is not None:
        return _CV_SCHEMA
    if not _SCHEMA_PATH:
        LOG.warning("Failed to load CV schema: schema path not available")
        return None
    try:
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            _CV_SCHEMA = json.load(f)
        return _CV_SCHEMA
    except Exception as e:
        LOG.warning("Failed to load CV schema: %s", e)
        return None


@dataclass(frozen=True)
class _RetryConfig:
    max_attempts: int = 8
    base_delay_s: float = 0.75
    max_delay_s: float = 20.0
    write_multiplier: float = 1.6
    deterministic: bool = False


def _strip_markdown_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```json"):
        text = text[len("```json") :]
    elif text.startswith("```"):
        text = text[len("```") :]
    if text.endswith("```"):
        text = text[: -len("```")]
    return text.strip()


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    """
    Robustly extract a JSON object from model output.

    Handles:
    - pure JSON
    - fenced code blocks
    - extra commentary around JSON
    """
    if not isinstance(text, str):
        return None

    cleaned = _strip_markdown_fences(text)

    # Fast path: exact JSON
    try:
        obj = json.loads(cleaned)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass

    # Attempt to locate the first top-level JSON object
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


class _OpenAIRetry:
    def __init__(self, *, retry: _RetryConfig, sleep: Callable[[float], None]):
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

    def _sleep_with_backoff(self, attempt_idx: int, *, is_write: bool, exc: Exception) -> None:
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


def _fetch_job_description(url: str) -> str:
    """
    Fetch job description from URL and extract/clean text content.

    Returns:
        Cleaned text content (max 5000 chars), or empty string if fetch fails.
    """
    if not requests:
        return ""
    try:
        resp = requests.get(
            url,
            timeout=15,
            headers={
                "User-Agent": "cvextract/1.0 (+https://example.invalid)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        if resp.status_code != 200:
            return ""

        html = resp.text or ""
        if not html:
            return ""

        # Remove script/style/noscript
        html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<noscript[^>]*>.*?</noscript>", "", html, flags=re.DOTALL | re.IGNORECASE)

        # Strip tags
        text = re.sub(r"<[^>]+>", " ", html)

        # Decode common HTML entities lightly (no extra deps)
        text = (
            text.replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&quot;", '"')
            .replace("&#39;", "'")
        )

        # Collapse whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Limit to avoid token blowups
        return text[:5000] if text else ""
    except Exception:
        return ""


class OpenAIJobSpecificAdjuster(CVAdjuster):
    """
    Adjuster that uses OpenAI to tailor CV based on a specific job description.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        *,
        retry_config: Optional[_RetryConfig] = None,
        _sleep: Callable[[float], None] = time.sleep,
    ):
        self._model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._retry = retry_config or _RetryConfig()
        self._sleep = _sleep

    def name(self) -> str:
        return "openai-job-specific"

    def description(self) -> str:
        return "Adjusts CV based on a specific job description using OpenAI"

    def validate_params(self, **kwargs) -> None:
        has_job_url = "job_url" in kwargs or "job-url" in kwargs
        has_job_desc = "job_description" in kwargs or "job-description" in kwargs

        if not has_job_url and not has_job_desc:
            raise ValueError(
                f"Adjuster '{self.name()}' requires either 'job-url' or 'job-description' parameter"
            )

        # If they provided the key but it's empty, still invalid
        job_desc_val = kwargs.get("job_description") or kwargs.get("job-description")
        job_url_val = kwargs.get("job_url") or kwargs.get("job-url")
        if (not job_desc_val) and (not job_url_val):
            raise ValueError(
                f"Adjuster '{self.name()}' requires either non-empty 'job-url' or 'job-description'"
            )

    def adjust(self, cv_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        self.validate_params(**kwargs)

        if not self._api_key or OpenAI is None:
            LOG.warning("Job-specific adjust skipped: OpenAI unavailable or API key missing.")
            return cv_data

        job_description = kwargs.get("job_description", kwargs.get("job-description", "")) or ""
        job_url = kwargs.get("job_url", kwargs.get("job-url", "")) or ""

        # Get job description from URL or direct text
        if not job_description and job_url:
            LOG.info("Fetching job description from %s", job_url)
            job_description = _fetch_job_description(job_url)
            if not job_description:
                LOG.warning("Job-specific adjust: failed to fetch job description from URL")
                return cv_data

        # Load prompt (keep typo key for compatibility, add fallback)
        system_prompt = format_prompt("adjuster_promp_for_specific_job", job_description=job_description)
        if not system_prompt:
            system_prompt = format_prompt("adjuster_prompt_for_specific_job", job_description=job_description)

        if not system_prompt:
            LOG.warning("Job-specific adjust skipped: failed to load prompt template")
            return cv_data

        client = OpenAI(api_key=self._api_key)
        retryer = _OpenAIRetry(retry=self._retry, sleep=self._sleep)

        user_payload = {
            "job_description": job_description,
            "original_json": cv_data,
            "adjusted_json": "",
        }

        # Single retry system (no stacked retries)
        try:
            completion = retryer.call(
                lambda: client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
                    ],
                    temperature=0.2,
                ),
                is_write=True,
                op_name="Job-specific adjust completion",
            )
        except Exception as e:
            LOG.warning("Job-specific adjust error (%s); using original JSON.", type(e).__name__)
            return cv_data

        content = None
        try:
            content = completion.choices[0].message.content if completion.choices else None
        except Exception:
            content = None

        if not content:
            LOG.warning("Job-specific adjust: empty completion; using original JSON.")
            return cv_data

        adjusted = _extract_json_object(content)
        if adjusted is None:
            LOG.warning("Job-specific adjust: invalid JSON response; using original JSON.")
            return cv_data

        # Validate adjusted CV against schema
        _ = _load_cv_schema()
        cv_verifier = get_verifier("cv-schema-verifier")
        if not cv_verifier:
            LOG.warning("Job-specific adjust: CV schema verifier not available; using original JSON.")
            return cv_data

        try:
            validation_result = cv_verifier.verify(adjusted)
        except Exception as e:
            LOG.warning("Job-specific adjust: schema validation error (%s); using original JSON.", type(e).__name__)
            return cv_data

        if validation_result.ok:
            LOG.info("The CV was adjusted to better fit the job description.")
            return adjusted

        LOG.warning(
            "Job-specific adjust: adjusted CV failed schema validation (%d errors); using original JSON.",
            len(getattr(validation_result, "errors", []) or []),
        )
        return cv_data
