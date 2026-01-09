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
import re
import time
from typing import Any, Callable, Dict, Optional

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

from ..shared import UnitOfWork, format_prompt
from .base import CVAdjuster
from .openai_utils import OpenAIRetry as _OpenAIRetry
from .openai_utils import RetryConfig as _RetryConfig
from .openai_utils import extract_json_object as _extract_json_object
from .openai_utils import (
    get_cached_resource_path,
)
from .openai_utils import strip_markdown_fences as _strip_markdown_fences

LOG = logging.getLogger("cvextract")

# CV schema cache (bundled-safe)
_CV_SCHEMA: Optional[Dict[str, Any]] = None


_SCHEMA_PATH = get_cached_resource_path("cv_schema.json")


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
        html = re.sub(
            r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE
        )
        html = re.sub(
            r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE
        )
        html = re.sub(
            r"<noscript[^>]*>.*?</noscript>", "", html, flags=re.DOTALL | re.IGNORECASE
        )

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
        request_timeout_s: float = 60.0,
        _sleep: Callable[[float], None] = time.sleep,
    ):
        self._model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._retry = retry_config or _RetryConfig()
        self._request_timeout_s = float(request_timeout_s)
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

    def adjust(self, work: UnitOfWork, **kwargs) -> UnitOfWork:
        cv_data = self._load_input_json(work)
        self.validate_params(**kwargs)

        if not self._api_key or OpenAI is None:
            LOG.warning(
                "Job-specific adjust skipped: OpenAI unavailable or API key missing."
            )
            return self._write_output_json(work, cv_data)

        job_description = (
            kwargs.get("job_description", kwargs.get("job-description", "")) or ""
        )
        job_url = kwargs.get("job_url", kwargs.get("job-url", "")) or ""

        # Get job description from URL or direct text
        if not job_description and job_url:
            LOG.info("Fetching job description from %s", job_url)
            job_description = _fetch_job_description(job_url)
            if not job_description:
                LOG.warning(
                    "Job-specific adjust: failed to fetch job description from URL"
                )
                return self._write_output_json(work, cv_data)

        # Load prompt (keep typo key for compatibility, add fallback)
        system_prompt = format_prompt(
            "adjuster_promp_for_specific_job", job_description=job_description
        )
        if not system_prompt:
            system_prompt = format_prompt(
                "adjuster_prompt_for_specific_job", job_description=job_description
            )

        if not system_prompt:
            LOG.warning("Job-specific adjust skipped: failed to load prompt template")
            return self._write_output_json(work, cv_data)

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
                        {
                            "role": "user",
                            "content": json.dumps(user_payload, ensure_ascii=False),
                        },
                    ],
                    temperature=0.2,
                    timeout=self._request_timeout_s,
                ),
                is_write=True,
                op_name="Job-specific adjust completion",
            )
        except Exception as e:
            LOG.warning(
                "Job-specific adjust error (%s); using original JSON.", type(e).__name__
            )
            return self._write_output_json(work, cv_data)

        content = None
        finish_reason = None
        try:
            if completion.choices:
                choice = completion.choices[0]
                finish_reason = getattr(choice, "finish_reason", None)
                content = choice.message.content
        except Exception:
            content = None
            finish_reason = None

        if isinstance(finish_reason, str) and finish_reason != "stop":
            LOG.warning(
                "Job-specific adjust: completion not finished (%s); using original JSON.",
                finish_reason,
            )
            return self._write_output_json(work, cv_data)

        if not content:
            LOG.warning("Job-specific adjust: empty completion; using original JSON.")
            return self._write_output_json(work, cv_data)

        adjusted = _extract_json_object(content)
        if adjusted is None:
            LOG.warning(
                "Job-specific adjust: invalid JSON response; using original JSON."
            )
            return self._write_output_json(work, cv_data)

        LOG.info("The CV was adjusted to better fit the job description.")
        return self._write_output_json(work, adjusted)
