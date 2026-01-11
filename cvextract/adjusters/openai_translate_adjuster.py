"""
OpenAI-based translation adjuster.

Translates CV JSON to a target language while preserving schema and identifiers.
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Callable, Dict, Iterable, List, Optional

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

from ..shared import UnitOfWork, format_prompt, load_input_json, write_output_json
from .base import CVAdjuster
from .openai_utils import OpenAIRetry as _OpenAIRetry
from .openai_utils import RetryConfig as _RetryConfig
from .openai_utils import extract_json_object as _extract_json_object
from .openai_utils import get_cached_resource_path

LOG = logging.getLogger("cvextract")

_CV_SCHEMA: Optional[Dict[str, Any]] = None
_SCHEMA_PATH = get_cached_resource_path("cv_schema.json")

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_URL_RE = re.compile(r"\bhttps?://[^\s\"']+\b")


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


def _validate_cv_data(data: Any, schema: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    if not isinstance(data, dict):
        return ["translated JSON must be an object"]

    required_fields = schema.get("required", [])
    for field in required_fields:
        if field not in data:
            errs.append(f"missing required field: {field}")

    if "identity" in data:
        identity = data["identity"]
        identity_props = schema.get("properties", {}).get("identity", {})
        identity_required = identity_props.get("required", [])
        for field in identity_required:
            if not identity or field not in identity:
                errs.append(f"identity missing required field: {field}")
            elif not isinstance(identity.get(field), str) or not identity.get(field):
                errs.append(f"identity.{field} must be a non-empty string")

    if "sidebar" in data:
        sidebar = data["sidebar"]
        if sidebar is not None and not isinstance(sidebar, dict):
            errs.append("sidebar must be an object")

    if "overview" in data:
        overview = data["overview"]
        if overview is not None and not isinstance(overview, str):
            errs.append("overview must be a string")

    if "experiences" in data:
        experiences = data["experiences"]
        if not isinstance(experiences, list):
            errs.append("experiences must be an array")
        else:
            for idx, exp in enumerate(experiences):
                if not isinstance(exp, dict):
                    errs.append(f"experiences[{idx}] must be an object")
                    continue

                if "heading" not in exp:
                    errs.append(f"experiences[{idx}] missing required field: heading")
                elif not isinstance(exp["heading"], str):
                    errs.append(f"experiences[{idx}].heading must be a string")

                if "description" not in exp:
                    errs.append(
                        f"experiences[{idx}] missing required field: description"
                    )
                elif not isinstance(exp["description"], str):
                    errs.append(f"experiences[{idx}].description must be a string")

                if "bullets" in exp:
                    if not isinstance(exp["bullets"], list):
                        errs.append(f"experiences[{idx}].bullets must be an array")
                    elif exp["bullets"] and not all(
                        isinstance(b, str) for b in exp["bullets"]
                    ):
                        errs.append(f"experiences[{idx}].bullets items must be strings")

                if "environment" in exp:
                    env = exp["environment"]
                    if env is not None and not isinstance(env, list):
                        errs.append(
                            f"experiences[{idx}].environment must be an array or null"
                        )
                    elif (
                        isinstance(env, list)
                        and env
                        and not all(isinstance(e, str) for e in env)
                    ):
                        errs.append(
                            f"experiences[{idx}].environment items must be strings"
                        )

    return errs


def _collect_protected_terms(cv_data: Dict[str, Any]) -> List[str]:
    terms: List[str] = []

    identity = cv_data.get("identity")
    if isinstance(identity, dict):
        for key in ("full_name", "first_name", "last_name"):
            value = identity.get(key)
            if isinstance(value, str) and value.strip():
                terms.append(value.strip())

    sidebar = cv_data.get("sidebar")
    if isinstance(sidebar, dict):
        for key in ("languages", "tools"):
            values = sidebar.get(key)
            if isinstance(values, list):
                for value in values:
                    if isinstance(value, str) and value.strip():
                        terms.append(value.strip())

    experiences = cv_data.get("experiences")
    if isinstance(experiences, list):
        for exp in experiences:
            if not isinstance(exp, dict):
                continue
            env = exp.get("environment")
            if isinstance(env, list):
                for value in env:
                    if isinstance(value, str) and value.strip():
                        terms.append(value.strip())

    seen = set()
    deduped = []
    for term in terms:
        if term in seen:
            continue
        seen.add(term)
        deduped.append(term)
    return deduped


class _TextProtector:
    def __init__(self, protected_terms: Iterable[str]) -> None:
        unique_terms = []
        seen = set()
        for term in protected_terms:
            if not term:
                continue
            if term in seen:
                continue
            seen.add(term)
            unique_terms.append(term)

        unique_terms.sort(key=len, reverse=True)
        self._term_patterns = [
            re.compile(rf"(?<!\w){re.escape(term)}(?!\w)") for term in unique_terms
        ]
        self._replacements: Dict[str, str] = {}

    def protect(self, text: str) -> str:
        text = _EMAIL_RE.sub(self._replace, text)
        text = _URL_RE.sub(self._replace, text)
        for pattern in self._term_patterns:
            text = pattern.sub(self._replace, text)
        return text

    def restore(self, text: str) -> str:
        for token, original in self._replacements.items():
            text = text.replace(token, original)
        return text

    def _replace(self, match: re.Match[str]) -> str:
        token = f"__PROTECTED_{len(self._replacements) + 1}__"
        self._replacements[token] = match.group(0)
        return token


def _map_strings(value: Any, fn: Callable[[str], str]) -> Any:
    if isinstance(value, dict):
        return {key: _map_strings(val, fn) for key, val in value.items()}
    if isinstance(value, list):
        return [_map_strings(item, fn) for item in value]
    if isinstance(value, str):
        return fn(value)
    return value


def _restore_protected_fields(
    original: Dict[str, Any], translated: Dict[str, Any]
) -> Dict[str, Any]:
    original_identity = original.get("identity")
    translated_identity = translated.get("identity")
    if isinstance(original_identity, dict) and isinstance(translated_identity, dict):
        for key in ("full_name", "first_name", "last_name"):
            if key in original_identity:
                translated_identity[key] = original_identity.get(key)

    original_sidebar = original.get("sidebar")
    translated_sidebar = translated.get("sidebar")
    if isinstance(original_sidebar, dict) and isinstance(translated_sidebar, dict):
        for key in ("languages", "tools"):
            if key in original_sidebar:
                translated_sidebar[key] = original_sidebar.get(key)

    original_exps = original.get("experiences")
    translated_exps = translated.get("experiences")
    if isinstance(original_exps, list) and isinstance(translated_exps, list):
        for idx, original_exp in enumerate(original_exps):
            if idx >= len(translated_exps):
                break
            translated_exp = translated_exps[idx]
            if not isinstance(original_exp, dict) or not isinstance(
                translated_exp, dict
            ):
                continue
            if "environment" in original_exp:
                translated_exp["environment"] = original_exp.get("environment")

    return translated


class OpenAITranslateAdjuster(CVAdjuster):
    """
    Adjuster that translates CV JSON into a target language.
    """

    def __init__(
        self,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        *,
        retry_config: Optional[_RetryConfig] = None,
        request_timeout_s: float = 60.0,
        temperature: float = 0.0,
        _sleep: Callable[[float], None] = time.sleep,
    ):
        self._model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._retry = retry_config or _RetryConfig()
        self._request_timeout_s = float(request_timeout_s)
        self._temperature = float(temperature)
        self._sleep = _sleep

    def name(self) -> str:
        return "openai-translate"

    def description(self) -> str:
        return "Translates CV JSON to a target language using OpenAI"

    def validate_params(self, **kwargs) -> None:
        language = kwargs.get("language") or kwargs.get("target-language")
        if language is None or not str(language).strip():
            raise ValueError(
                f"Adjuster '{self.name()}' requires non-empty 'language' parameter"
            )

    def adjust(self, work: UnitOfWork, **kwargs) -> UnitOfWork:
        cv_data = load_input_json(work)
        self.validate_params(**kwargs)

        if not self._api_key or OpenAI is None:
            LOG.warning(
                "Translate adjust skipped: OpenAI unavailable or API key missing."
            )
            return write_output_json(work, cv_data)

        schema = _load_cv_schema()
        if not schema:
            LOG.warning("Translate adjust skipped: CV schema unavailable.")
            return write_output_json(work, cv_data)

        language = str(kwargs.get("language") or kwargs.get("target-language")).strip()
        protected_terms = _collect_protected_terms(cv_data)
        system_prompt = format_prompt(
            "adjuster_prompt_translate_cv",
            language=language,
            schema=json.dumps(schema, ensure_ascii=False, indent=2),
            protected_terms=json.dumps(protected_terms, ensure_ascii=False),
        )
        if not system_prompt:
            LOG.warning("Translate adjust skipped: failed to load prompt template.")
            return write_output_json(work, cv_data)

        protector = _TextProtector(protected_terms)
        protected_cv = _map_strings(cv_data, protector.protect)

        user_payload = {
            "language": language,
            "original_json": protected_cv,
            "translated_json": "",
        }

        temperature = kwargs.get("temperature", self._temperature)
        try:
            temperature = float(temperature)
        except (TypeError, ValueError):
            LOG.warning("Translate adjust: invalid temperature, using default.")
            temperature = self._temperature

        client = OpenAI(api_key=self._api_key)
        retryer = _OpenAIRetry(retry=self._retry, sleep=self._sleep)

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
                    temperature=temperature,
                    timeout=self._request_timeout_s,
                ),
                is_write=True,
                op_name="Translate CV completion",
            )
        except Exception as e:
            LOG.warning(
                "Translate adjust error (%s); using original JSON.", type(e).__name__
            )
            return write_output_json(work, cv_data)

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
                "Translate adjust: completion not finished (%s); using original JSON.",
                finish_reason,
            )
            return write_output_json(work, cv_data)

        if not content:
            LOG.warning("Translate adjust: empty completion; using original JSON.")
            return write_output_json(work, cv_data)

        translated = _extract_json_object(content)
        if translated is None:
            LOG.warning("Translate adjust: invalid JSON response; using original JSON.")
            return write_output_json(work, cv_data)

        translated = _map_strings(translated, protector.restore)
        translated = _restore_protected_fields(cv_data, translated)

        errs = _validate_cv_data(translated, schema)
        if errs:
            LOG.warning(
                "Translate adjust: schema validation failed: %s; using original JSON.",
                "; ".join(errs),
            )
            return write_output_json(work, cv_data)

        LOG.info("Translated CV to %s.", language)
        return write_output_json(work, translated)
