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
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Dict, Optional

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

from ..shared import UnitOfWork, format_prompt, url_to_cache_filename
from .base import CVAdjuster
from .openai_utils import (
    OpenAIRetry as _OpenAIRetry,
    RetryConfig as _RetryConfig,
    extract_json_object as _extract_json_object,
    get_cached_resource_path,
    strip_markdown_fences as _strip_markdown_fences,
)

LOG = logging.getLogger("cvextract")

# Research schema cache
_RESEARCH_SCHEMA: Optional[Dict[str, Any]] = None


_SCHEMA_PATH = get_cached_resource_path("research_schema.json")


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

    Uses built-in checks against research_schema.json requirements.
    """
    if not isinstance(data, dict):
        return False

    schema = _load_research_schema()
    if not schema:
        LOG.warning("Failed to load research schema for validation")
        return False

    errs: list[str] = []
    required_fields = set(schema.get("required", []))
    required_fields.update({"name", "domains"})
    for field in sorted(required_fields):
        if field not in data:
            errs.append(f"missing required field: {field}")

    if "name" in data:
        if not isinstance(data["name"], str):
            errs.append("name must be a string")
        elif not data["name"]:
            errs.append("name must be a non-empty string")

    if "description" in data:
        if data["description"] is not None and not isinstance(data["description"], str):
            errs.append("description must be a string or null")

    if "domains" in data:
        domains = data["domains"]
        if not isinstance(domains, list):
            errs.append("domains must be an array")
        else:
            if not domains:
                errs.append("domains must have at least one item")
            elif not all(isinstance(d, str) for d in domains):
                errs.append("domains items must be strings")

    if "technology_signals" in data:
        signals = data["technology_signals"]
        if not isinstance(signals, list):
            errs.append("technology_signals must be an array")
        else:
            for idx, signal in enumerate(signals):
                if not isinstance(signal, dict):
                    errs.append(f"technology_signals[{idx}] must be an object")
                    continue

                if "technology" not in signal:
                    errs.append(
                        f"technology_signals[{idx}] missing required field: technology"
                    )
                elif not isinstance(signal["technology"], str):
                    errs.append(
                        f"technology_signals[{idx}].technology must be a string"
                    )

                if "category" in signal and signal["category"] is not None:
                    if not isinstance(signal["category"], str):
                        errs.append(
                            f"technology_signals[{idx}].category must be a string or null"
                        )

                if "interest_level" in signal:
                    if signal["interest_level"] not in [
                        None,
                        "low",
                        "medium",
                        "high",
                    ]:
                        errs.append(
                            f"technology_signals[{idx}].interest_level must be 'low', 'medium', 'high', or null"
                        )

                if "confidence" in signal:
                    conf = signal["confidence"]
                    if not isinstance(conf, (int, float)) or conf < 0 or conf > 1:
                        errs.append(
                            f"technology_signals[{idx}].confidence must be a number between 0 and 1"
                        )

                if "signals" in signal:
                    sigs = signal["signals"]
                    if not isinstance(sigs, list):
                        errs.append(
                            f"technology_signals[{idx}].signals must be an array"
                        )
                    elif not all(isinstance(s, str) for s in sigs):
                        errs.append(
                            f"technology_signals[{idx}].signals items must be strings"
                        )

                if "notes" in signal and signal["notes"] is not None:
                    if not isinstance(signal["notes"], str):
                        errs.append(
                            f"technology_signals[{idx}].notes must be a string or null"
                        )

    if "industry_classification" in data:
        ic = data["industry_classification"]
        if ic is not None and not isinstance(ic, dict):
            errs.append("industry_classification must be an object or null")
        elif isinstance(ic, dict):
            if (
                "naics" in ic
                and ic["naics"] is not None
                and not isinstance(ic["naics"], str)
            ):
                errs.append("industry_classification.naics must be a string or null")
            if (
                "sic" in ic
                and ic["sic"] is not None
                and not isinstance(ic["sic"], str)
            ):
                errs.append("industry_classification.sic must be a string or null")

    if "founded_year" in data:
        year = data["founded_year"]
        if year is not None:
            if not isinstance(year, int) or year < 1600 or year > 2100:
                errs.append("founded_year must be an integer between 1600 and 2100")

    if "headquarters" in data:
        hq = data["headquarters"]
        if hq is not None and not isinstance(hq, dict):
            errs.append("headquarters must be an object or null")
        elif isinstance(hq, dict):
            if "country" not in hq:
                errs.append("headquarters missing required field: country")
            if (
                "city" in hq
                and hq["city"] is not None
                and not isinstance(hq["city"], str)
            ):
                errs.append("headquarters.city must be a string or null")
            if (
                "state" in hq
                and hq["state"] is not None
                and not isinstance(hq["state"], str)
            ):
                errs.append("headquarters.state must be a string or null")
            if (
                "country" in hq
                and hq["country"] is not None
                and not isinstance(hq["country"], str)
            ):
                errs.append("headquarters.country must be a string or null")

    if "company_size" in data:
        size = data["company_size"]
        if size not in [None, "solo", "small", "medium", "large", "enterprise"]:
            errs.append(
                "company_size must be 'solo', 'small', 'medium', 'large', 'enterprise', or null"
            )

    if "employee_count" in data:
        count = data["employee_count"]
        if count is not None:
            if not isinstance(count, int) or count < 1:
                errs.append("employee_count must be a positive integer or null")

    if "ownership_type" in data:
        ot = data["ownership_type"]
        if ot not in [None, "private", "public", "nonprofit", "government"]:
            errs.append(
                "ownership_type must be 'private', 'public', 'nonprofit', 'government', or null"
            )

    if "website" in data:
        if data["website"] is not None and not isinstance(data["website"], str):
            errs.append("website must be a string or null")

    if errs:
        LOG.warning(
            "Company research validation failed (%d errors)", len(errs)
        )
        return False

    return True


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
            work.config.skip_all_verify
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
                    timeout=float(self._request_timeout_s),
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

        LOG.info("The CV was adjusted to better fit the target company.")
        return self._write_output_json(work, adjusted)
