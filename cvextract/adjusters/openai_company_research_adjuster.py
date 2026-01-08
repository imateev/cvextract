"""
OpenAI-based company research adjuster.

Adjusts CV data based on target company research using OpenAI.

Improvements included:
- Centralized retry/backoff with jitter for 429/5xx/transient network errors
- Honors Retry-After when present
- Safer JSON extraction from model output (handles fenced blocks and pre/post text)
- More robust cache handling + atomic writes
- Optional deterministic retry/jitter for tests
- Fixes small prompt template typo compatibility (keeps legacy key)
- Better schema loading + validation guardrails
"""

from __future__ import annotations

import json
import logging
import os
import random
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, Optional, TypeVar

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

try:
    # Python 3.9+
    from importlib.resources import as_file, files
except ModuleNotFoundError:
    # Python < 3.9 backport
    from importlib_resources import files, as_file  # type: ignore

from ..shared import UnitOfWork, format_prompt, url_to_cache_filename
from ..verifiers import get_verifier
from .base import CVAdjuster

LOG = logging.getLogger("cvextract")

T = TypeVar("T")


# Research schema cache
_RESEARCH_SCHEMA: Optional[Dict[str, Any]] = None


def _get_research_schema_path() -> Optional[Path]:
    """Get path to research schema, handling bundled executables (PyInstaller)."""
    try:
        schema_resource = files("cvextract.contracts").joinpath("research_schema.json")

        # Cache to a stable location so returning Path is safe even after `as_file` closes.
        cache_dir = Path(tempfile.gettempdir()) / "cvextract"
        cache_dir.mkdir(parents=True, exist_ok=True)

        cache_path = cache_dir / "research_schema.json"
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


_SCHEMA_PATH = _get_research_schema_path()


@dataclass(frozen=True)
class _RetryConfig:
    max_attempts: int = 8
    base_delay_s: float = 0.75
    max_delay_s: float = 20.0
    write_multiplier: float = 1.6
    deterministic: bool = False


def _atomic_write_json(path: Path, data: Dict[str, Any]) -> None:
    """Write JSON atomically to avoid cache corruption on crash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", delete=False, encoding="utf-8", dir=str(path.parent)
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def _load_cached_research(
    cache_path: Path, *, skip_verify: bool = False
) -> Optional[Dict[str, Any]]:
    if not cache_path.exists():
        return None
    try:
        with cache_path.open("r", encoding="utf-8") as f:
            cached_data = json.load(f)
        if not isinstance(cached_data, dict):
            return None
        if skip_verify:
            LOG.info(
                "Using cached company research from %s (verification skipped)",
                cache_path,
            )
            return cached_data
        if _validate_research_data(cached_data):
            LOG.info("Using cached company research from %s", cache_path)
            return cached_data
        LOG.warning("Cached company research failed validation, will re-research")
    except Exception as e:
        LOG.warning(
            "Failed to load cached research (%s), will re-research", type(e).__name__
        )
    return None


def _cache_research_data(cache_path: Path, research_data: Dict[str, Any]) -> None:
    try:
        _atomic_write_json(cache_path, research_data)
        LOG.info("Cached company research to %s", cache_path)
    except Exception as e:
        LOG.warning("Failed to cache research (%s)", type(e).__name__)


def _load_research_schema() -> Optional[Dict[str, Any]]:
    """Load the research schema from file (cached)."""
    global _RESEARCH_SCHEMA
    if _RESEARCH_SCHEMA is not None:
        return _RESEARCH_SCHEMA
    if not _SCHEMA_PATH:
        LOG.warning("Failed to load research schema: schema path not available")
        return None
    try:
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            _RESEARCH_SCHEMA = json.load(f)
        return _RESEARCH_SCHEMA
    except Exception as e:
        LOG.warning("Failed to load research schema: %s", e)
        return None


def _fetch_customer_page(url: str) -> str:
    """Fetch the content of a URL (best-effort)."""
    if not requests:
        return ""
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return ""
        return resp.text or ""
    except Exception:
        return ""


def _validate_research_data(data: Any) -> bool:
    """
    Validate that research data conforms to the company profile schema.

    Uses the CompanyProfileVerifier to ensure the data structure
    matches the research_schema.json requirements.
    """
    if not isinstance(data, dict):
        return False

    try:
        verifier = get_verifier("company-profile-verifier")
        if not verifier:
            LOG.warning("CompanyProfileVerifier not available")
            return False
        result = verifier.verify(data=data)
        return bool(result.ok)
    except Exception as e:
        LOG.warning("Failed to validate research data with verifier: %s", e)
        return False


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

    Returns:
        dict if found and parsed, else None
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

    # Try to find a top-level JSON object by scanning for {...}
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
    def __init__(
        self,
        *,
        retry: _RetryConfig,
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


def _research_company_profile(
    customer_url: str,
    api_key: str,
    model: str,
    *,
    retry: Optional[_RetryConfig] = None,
    sleep: Callable[[float], None] = time.sleep,
    request_timeout_s: float = 60.0,
    skip_verify: bool = False,
) -> Optional[Dict[str, Any]]:
    """
    Research a company profile from its URL using OpenAI.

    Returns:
        Dict containing company profile data, or None if research fails
    """
    if not OpenAI:
        LOG.warning("Company research skipped: OpenAI unavailable")
        return None

    schema = _load_research_schema()
    if not schema:
        LOG.warning("Company research skipped: schema not available")
        return None

    research_prompt = format_prompt(
        "website_analysis_prompt",
        customer_url=customer_url,
        schema=json.dumps(schema, indent=2),
    )
    if not research_prompt:
        LOG.warning("Company research skipped: failed to load prompt template")
        return None

    client = OpenAI(api_key=api_key)
    retryer = _OpenAIRetry(retry=retry or _RetryConfig(), sleep=sleep)

    try:
        completion = retryer.call(
            lambda: client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": research_prompt}],
                temperature=0.2,
                timeout=float(request_timeout_s),
            ),
            is_write=True,
            op_name="Company research completion",
        )
    except Exception as e:
        LOG.warning("Company research error (%s)", type(e).__name__)
        return None

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
        LOG.warning("Company research: completion not finished (%s)", finish_reason)
        return None

    if not content:
        LOG.warning("Company research: empty completion")
        return None

    research_data = _extract_json_object(content)
    if not research_data:
        LOG.warning("Company research: invalid JSON response")
        return None

    if skip_verify:
        return research_data

    if not _validate_research_data(research_data):
        LOG.warning("Company research: response failed schema validation")
        return None

    LOG.info("Successfully researched company profile")
    return research_data


class OpenAICompanyResearchAdjuster(CVAdjuster):
    """
    Adjuster that uses OpenAI to tailor CV based on company research.
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
        """
        Initialize the adjuster.

        Args:
            model: OpenAI model to use (default: "gpt-4o-mini")
            api_key: Optional OpenAI API key (defaults to OPENAI_API_KEY env var)
            retry_config: Retry/backoff configuration for OpenAI calls
            _sleep: Injected sleep (tests)
        """
        self._model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._retry = retry_config or _RetryConfig()
        self._request_timeout_s = float(request_timeout_s)
        self._sleep = _sleep

    def name(self) -> str:
        return "openai-company-research"

    def description(self) -> str:
        return "Adjusts CV based on target company research using OpenAI"

    def validate_params(self, **kwargs) -> None:
        has_customer_url = "customer_url" in kwargs or "customer-url" in kwargs
        if not has_customer_url or not (
            kwargs.get("customer_url") or kwargs.get("customer-url")
        ):
            raise ValueError(
                f"Adjuster '{self.name()}' requires 'customer-url' parameter"
            )

    def adjust(self, work: UnitOfWork, **kwargs) -> UnitOfWork:
        cv_data = self._load_input_json(work)
        self.validate_params(**kwargs)

        if not self._api_key or OpenAI is None:
            LOG.warning(
                "Company research adjust skipped: OpenAI unavailable or API key missing."
            )
            return self._write_output_json(work, cv_data)

        customer_url = kwargs.get("customer_url", kwargs.get("customer-url"))
        skip_verify = bool(
            work.config.skip_verify
            or (work.config.adjust and work.config.adjust.skip_verify)
        )
        cache_dir = work.config.workspace.research_dir
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / url_to_cache_filename(customer_url)
        research_data = _load_cached_research(cache_path, skip_verify=skip_verify)

        # Step 1: Research company profile (with retries)
        if not research_data:
            LOG.info("Researching company at %s", customer_url)
            research_data = _research_company_profile(
                customer_url,
                self._api_key,
                self._model,
                retry=self._retry,
                sleep=self._sleep,
                request_timeout_s=self._request_timeout_s,
                skip_verify=skip_verify,
            )
            if research_data:
                _cache_research_data(cache_path, research_data)

        if not research_data:
            LOG.warning(
                "Company research adjust: failed to research company; using original CV."
            )
            return self._write_output_json(work, cv_data)

        # Step 2: Build research context text
        domains_text = (
            ", ".join(research_data.get("domains", []))
            if isinstance(research_data.get("domains"), list)
            else ""
        )
        company_name = research_data.get("name", "the company")
        company_desc = research_data.get("description", "") or ""

        tech_signals_parts: list[str] = []
        tech_signals = research_data.get("technology_signals")
        if isinstance(tech_signals, list) and tech_signals:
            tech_signals_parts.append("Key Technology Signals:")
            for signal in tech_signals:
                if not isinstance(signal, dict):
                    continue
                tech = signal.get("technology", "Unknown")
                interest = signal.get("interest_level", "unknown")
                confidence = signal.get("confidence", 0)
                evidence = signal.get("signals", [])

                try:
                    conf_str = f"{float(confidence):.2f}"
                except (TypeError, ValueError):
                    conf_str = "0.00"

                tech_signals_parts.append(
                    f"\n- {tech} (interest: {interest}, confidence: {conf_str})"
                )
                if isinstance(evidence, list) and evidence:
                    tech_signals_parts.append(
                        f"\n  Evidence: {'; '.join([str(x) for x in evidence[:2]])}"
                    )

        tech_signals_text = "".join(tech_signals_parts)

        research_context = f"Company: {company_name}\n"
        if company_desc:
            research_context += f"Description: {company_desc}\n"
        if domains_text:
            research_context += f"Domains: {domains_text}\n"
        if tech_signals_text:
            research_context += tech_signals_text

        # Step 3: Load system prompt template with research context
        # Keep legacy template name (typo) for compatibility.
        system_prompt = format_prompt(
            "adjuster_promp_for_a_company", research_context=research_context
        )
        if not system_prompt:
            # Try a corrected template key as a fallback if it exists in your prompts.
            system_prompt = format_prompt(
                "adjuster_prompt_for_a_company", research_context=research_context
            )

        if not system_prompt:
            LOG.warning(
                "Company research adjust: failed to load prompt template; using original CV."
            )
            return self._write_output_json(work, cv_data)

        # Step 4: Create user payload with research data and cv_data
        user_payload = {
            "company_research": research_data,
            "original_json": cv_data,
            "adjusted_json": "",
        }

        client = OpenAI(api_key=self._api_key)
        retryer = _OpenAIRetry(retry=self._retry, sleep=self._sleep)

        # Step 5: Call OpenAI (with retries)
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
                ),
                is_write=True,
                op_name="Company research adjust completion",
            )
        except Exception as e:
            LOG.warning(
                "Company research adjust: API call failed (%s); using original CV.",
                type(e).__name__,
            )
            return self._write_output_json(work, cv_data)

        content = None
        try:
            content = (
                completion.choices[0].message.content if completion.choices else None
            )
        except Exception:
            content = None

        if not content:
            LOG.warning("Company research adjust: empty response; using original CV.")
            return self._write_output_json(work, cv_data)

        adjusted = _extract_json_object(content)
        if adjusted is None:
            LOG.warning(
                "Company research adjust: failed to parse JSON response; using original CV."
            )
            return self._write_output_json(work, cv_data)

        # Step 6: Validate adjusted CV against schema
        if not isinstance(adjusted, dict):
            LOG.warning(
                "Company research adjust: result is not a dict; using original CV."
            )
            return self._write_output_json(work, cv_data)

        if skip_verify:
            LOG.info("Company research adjust: verification skipped.")
            return self._write_output_json(work, adjusted)

        try:
            verifier_name = "cv-schema-verifier"
            if work.config.adjust and work.config.adjust.verifier:
                verifier_name = work.config.adjust.verifier
            cv_verifier = get_verifier(verifier_name)
            if not cv_verifier:
                LOG.warning(
                    "Company research adjust: verifier '%s' not available; using original CV.",
                    verifier_name,
                )
                return self._write_output_json(work, cv_data)

            validation_result = cv_verifier.verify(data=adjusted)
            if validation_result.ok:
                LOG.info("The CV was adjusted to better fit the target company.")
                return self._write_output_json(work, adjusted)

            LOG.warning(
                "Company research adjust: adjusted CV failed schema validation (%d errors); using original CV.",
                len(getattr(validation_result, "errors", []) or []),
            )
            return self._write_output_json(work, cv_data)

        except Exception as e:
            LOG.warning(
                "Company research adjust: schema validation error (%s); using original CV.",
                type(e).__name__,
            )
            return self._write_output_json(work, cv_data)
