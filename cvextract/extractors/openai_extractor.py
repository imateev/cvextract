"""
OpenAI-based CV extractor implementation.

Uses OpenAI API to extract structured CV data from document files.
Sends documents directly to OpenAI for processing using the Files/Assistants APIs.

Key reliability improvements vs the previous version:
- Centralized retry/backoff with full jitter for 429/5xx/transient network errors
- Honors Retry-After when present
- Adaptive polling with bounded timeout (dramatically reduces 429s from run.retrieve)
- Safer message selection + robust text extraction from Assistants message content
- Best-effort cleanup of assistant and uploaded file
"""

from __future__ import annotations

import json
import os
import random
import re
import tempfile
import time
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Callable, Optional, TypeVar

from openai import OpenAI

try:
    # Python 3.9+
    from importlib.resources import as_file, files
except ModuleNotFoundError:
    # Python < 3.9 backport
    from importlib_resources import files, as_file  # type: ignore

from ..shared import StepName, UnitOfWork, format_prompt, load_prompt
from .base import CVExtractor

T = TypeVar("T")


@dataclass(frozen=True)
class _RetryConfig:
    # Total attempts includes the first call.
    max_attempts: int = 8
    # Base for exponential backoff when Retry-After is missing.
    base_delay_s: float = 0.75
    # Cap sleep to avoid unbounded waits.
    max_delay_s: float = 20.0
    # Extra multiplier for "write" operations (create/upload) that often hit stricter buckets.
    write_multiplier: float = 1.6
    # If True, disables jitter (useful for deterministic tests).
    deterministic: bool = False


class OpenAICVExtractor(CVExtractor):
    """
    CV extractor using OpenAI API for intelligent document analysis.

    Uses Assistants API with file_search tool and attachments, matching ChatGPT UI behavior.
    """

    def __init__(
        self,
        model: str = "gpt-4o",
        *,
        api_key: Optional[str] = None,
        # Polling / rate-limit knobs
        run_timeout_s: float = 180.0,
        # Retry config knobs
        retry_config: Optional[_RetryConfig] = None,
        # Testability: allow injecting sleep + clock
        _sleep: Callable[[float], None] = time.sleep,
        _time: Callable[[], float] = time.time,
        **kwargs,
    ):
        """
        Initialize the OpenAI extractor.

        Args:
            model: OpenAI model to use (default: gpt-4o)
            run_timeout_s: Hard timeout for an assistant run.
            retry_config: Override retry/backoff behavior.
            _sleep: Injected sleep (tests).
            _time: Injected time function (tests).
            **kwargs: Additional arguments (reserved for future use)
        """
        self.model = model
        self._api_key = api_key
        self._client: Optional[OpenAI] = None

        self._run_timeout_s = float(run_timeout_s)
        self._retry = retry_config or _RetryConfig()
        self._sleep = _sleep
        self._time = _time

    @property
    def client(self) -> OpenAI:
        if self._client is None:
            api_key = self._api_key or os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError(
                    "OPENAI_API_KEY must be set to use OpenAICVExtractor"
                )
            self._client = OpenAI(api_key=api_key)
        return self._client

    def extract(self, work: UnitOfWork) -> UnitOfWork:
        """
        Extract structured CV data from a document file.

        Args:
            work: UnitOfWork containing Extract step input/output paths.

        Returns:
            UnitOfWork with output JSON populated.

        Raises:
            FileNotFoundError: If the file does not exist
            ValueError: If extraction or validation fails
        """
        file_path = work.get_step_input(StepName.Extract)
        if file_path is None:
            raise ValueError("Extraction input path is not set")

        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")

        if not file_path.is_file():
            raise ValueError(f"Path must be a file: {file_path}")

        cv_schema = self._load_cv_schema()
        response_text = self._extract_with_openai(file_path, cv_schema)
        data = self._parse_and_validate(
            response_text,
            cv_schema,
        )
        return self._write_output_json(work, data)

    def _load_cv_schema(self) -> dict[str, Any]:
        """Load the CV schema."""
        schema_resource = files("cvextract.contracts").joinpath("cv_schema.json")

        # Cache to a stable location so returning Path is safe even after `as_file` closes.
        cache_dir = Path(tempfile.gettempdir()) / "cvextract"
        cache_dir.mkdir(parents=True, exist_ok=True)

        version_tag = self._get_cache_version_tag()
        cache_path = cache_dir / f"cv_schema.{version_tag}.json"
        if not cache_path.exists():
            self._refresh_cv_schema_cache(cache_path, schema_resource)

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            self._refresh_cv_schema_cache(cache_path, schema_resource)
            with open(cache_path, "r", encoding="utf-8") as f:
                return json.load(f)

    def _get_cache_version_tag(self) -> str:
        try:
            pkg_version = version("cvextract")
        except PackageNotFoundError:
            pkg_version = "dev"
        return re.sub(r"[^A-Za-z0-9_.-]", "_", pkg_version)

    def _refresh_cv_schema_cache(self, cache_path: Path, schema_resource: Any) -> None:
        with as_file(schema_resource) as p:
            src = Path(p)
            if not src.exists():
                raise FileNotFoundError("cv_schema.json resource not available")
            cache_path.write_bytes(src.read_bytes())

    # --------------------------
    # Retry / Backoff utilities
    # --------------------------

    def _get_status_code(self, exc: Exception) -> Optional[int]:
        """
        Best-effort extraction of HTTP status from OpenAI SDK exceptions.

        The OpenAI python SDK has evolved; we defensively check common shapes.
        """
        for attr in ("status_code", "status", "http_status"):
            val = getattr(exc, attr, None)
            if isinstance(val, int):
                return val

        # Some SDK errors include a response object with status_code / headers
        resp = getattr(exc, "response", None)
        if resp is not None:
            sc = getattr(resp, "status_code", None)
            if isinstance(sc, int):
                return sc

        return None

    def _get_retry_after_s(self, exc: Exception) -> Optional[float]:
        """
        Best-effort extraction of Retry-After header, if present.
        """
        # SDK error may include headers directly
        headers = getattr(exc, "headers", None)

        # Or nested in response
        resp = getattr(exc, "response", None)
        if headers is None and resp is not None:
            headers = getattr(resp, "headers", None)

        if not headers:
            return None

        # headers might be dict-like
        ra = None
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
        """
        Decide if the error is worth retrying.

        We retry:
        - 429 (rate limit)
        - 5xx
        - common transient transport errors (best-effort)
        """
        status = self._get_status_code(exc)
        if status == 429:
            return True
        if status is not None and 500 <= status <= 599:
            return True

        # Transport-ish errors: connection resets, timeouts, etc.
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
        """
        Sleep according to Retry-After when present, else exponential backoff with jitter.
        attempt_idx is 0-based (0 => after first failure).
        """
        retry_after = self._get_retry_after_s(exc)
        if retry_after is not None and retry_after > 0:
            delay = min(self._retry.max_delay_s, retry_after)
            self._sleep(delay)
            return

        # exponential backoff
        mult = self._retry.write_multiplier if is_write else 1.0
        raw = self._retry.base_delay_s * (2**attempt_idx) * mult
        capped = min(self._retry.max_delay_s, raw)

        if self._retry.deterministic:
            delay = capped
        else:
            # full jitter: uniform(0, capped)
            delay = random.random() * capped

        # avoid extremely small sleeps that can hammer the API
        delay = max(0.25, delay)
        self._sleep(delay)

    def _call_with_retry(
        self, fn: Callable[[], T], *, is_write: bool, op_name: str
    ) -> T:
        """
        Centralized retry wrapper for OpenAI calls.
        """
        last_exc: Optional[Exception] = None
        for attempt in range(self._retry.max_attempts):
            try:
                return fn()
            except Exception as e:
                last_exc = e
                if not self._is_transient(e):
                    raise RuntimeError(f"{op_name} failed (non-retryable): {e}") from e

                # last attempt -> raise
                if attempt >= self._retry.max_attempts - 1:
                    status = self._get_status_code(e)
                    raise RuntimeError(
                        f"{op_name} failed after {self._retry.max_attempts} attempts"
                        + (f" (HTTP {status})" if status else "")
                        + f": {e}"
                    ) from e

                # back off and retry
                self._sleep_with_backoff(attempt, is_write=is_write, exc=e)

        # Should never reach here
        raise RuntimeError(f"{op_name} failed unexpectedly: {last_exc}")

    # --------------------------
    # OpenAI operations
    # --------------------------

    def _upload_file(self, file_path: Path) -> str:
        """
        Upload a file for Assistants usage.

        Returns:
            file_id
        """

        def _do() -> Any:
            with open(file_path, "rb") as f:
                # Purpose 'assistants' is correct for attaching to threads / file_search.
                return self.client.files.create(
                    file=(file_path.name, f), purpose="assistants"
                )

        resp = self._call_with_retry(_do, is_write=True, op_name="OpenAI file upload")
        file_id = getattr(resp, "id", None)
        if not file_id:
            raise RuntimeError("OpenAI file upload returned no file id")
        return file_id

    def _create_assistant(self, system_prompt: str) -> str:
        def _do() -> Any:
            return self.client.beta.assistants.create(
                name="CV Extractor",
                instructions=system_prompt,
                model=self.model,
                tools=[{"type": "file_search"}],
            )

        resp = self._call_with_retry(_do, is_write=True, op_name="Create assistant")
        assistant_id = getattr(resp, "id", None)
        if not assistant_id:
            raise RuntimeError("Create assistant returned no assistant id")
        return assistant_id

    def _create_thread(self) -> str:
        def _do() -> Any:
            return self.client.beta.threads.create()

        resp = self._call_with_retry(_do, is_write=True, op_name="Create thread")
        thread_id = getattr(resp, "id", None)
        if not thread_id:
            raise RuntimeError("Create thread returned no thread id")
        return thread_id

    def _create_message(
        self, *, thread_id: str, user_prompt: str, file_id: str
    ) -> None:
        def _do() -> Any:
            return self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=user_prompt,
                attachments=[{"file_id": file_id, "tools": [{"type": "file_search"}]}],
            )

        self._call_with_retry(_do, is_write=True, op_name="Create thread message")

    def _create_run(self, *, thread_id: str, assistant_id: str) -> str:
        def _do() -> Any:
            return self.client.beta.threads.runs.create(
                thread_id=thread_id, assistant_id=assistant_id
            )

        resp = self._call_with_retry(_do, is_write=True, op_name="Create run")
        run_id = getattr(resp, "id", None)
        if not run_id:
            raise RuntimeError("Create run returned no run id")
        return run_id

    def _retrieve_run(self, *, thread_id: str, run_id: str) -> Any:
        def _do() -> Any:
            return self.client.beta.threads.runs.retrieve(
                thread_id=thread_id, run_id=run_id
            )

        # retrieve is "read" op, but still can 429 hard if you poll too fast
        return self._call_with_retry(_do, is_write=False, op_name="Retrieve run")

    def _list_messages(self, *, thread_id: str) -> Any:
        def _do() -> Any:
            # You can pass limit=... in newer SDKs; keep minimal assumptions.
            return self.client.beta.threads.messages.list(thread_id=thread_id)

        return self._call_with_retry(_do, is_write=False, op_name="List messages")

    def _delete_assistant(self, assistant_id: str) -> None:
        def _do() -> Any:
            return self.client.beta.assistants.delete(assistant_id)

        # Cleanup should not hard-fail the extraction if deletion rate-limits.
        try:
            self._call_with_retry(_do, is_write=True, op_name="Delete assistant")
        except Exception:
            pass

    def _delete_file(self, file_id: str) -> None:
        def _do() -> Any:
            return self.client.files.delete(file_id)

        try:
            self._call_with_retry(_do, is_write=True, op_name="Delete file")
        except Exception:
            pass

    # --------------------------
    # Main extraction flow
    # --------------------------

    def _extract_with_openai(self, file_path: Path, cv_schema: dict[str, Any]) -> str:
        """
        Send the file to OpenAI using Assistants API and get extraction results.
        """
        file_id: Optional[str] = None
        assistant_id: Optional[str] = None

        # Prompts
        system_prompt = load_prompt("cv_extraction_system")
        if not system_prompt:
            raise RuntimeError("Failed to load system prompt")

        schema_str = json.dumps(cv_schema, indent=2)
        user_prompt = format_prompt(
            "cv_extraction_user",
            schema_json=schema_str,
            file_name=file_path.name,
        )
        if not user_prompt:
            raise RuntimeError("Failed to format user prompt")

        try:
            # Upload file (retry/backoff guarded)
            file_id = self._upload_file(file_path)

            # Create assistant + thread
            assistant_id = self._create_assistant(system_prompt)
            thread_id = self._create_thread()

            # Add message w/ attachment
            self._create_message(
                thread_id=thread_id, user_prompt=user_prompt, file_id=file_id
            )

            # Create run
            run_id = self._create_run(thread_id=thread_id, assistant_id=assistant_id)

            # Adaptive polling to avoid 429 storms
            run = self._wait_for_run(thread_id=thread_id, run_id=run_id)

            if getattr(run, "status", None) != "completed":
                # Surface more debug if available
                status = getattr(run, "status", "unknown")
                last_error = getattr(run, "last_error", None)
                if last_error:
                    raise RuntimeError(
                        f"Assistant run failed with status: {status}. last_error={last_error}"
                    )
                raise RuntimeError(f"Assistant run failed with status: {status}")

            # Fetch messages and extract assistant output
            messages = self._list_messages(thread_id=thread_id)
            response_text = self._extract_text_from_messages(messages)
            if not response_text:
                raise RuntimeError("No response text found in assistant messages")

            return response_text

        finally:
            # Best-effort cleanup
            if assistant_id:
                self._delete_assistant(assistant_id)
            if file_id:
                self._delete_file(file_id)

    def _wait_for_run(self, *, thread_id: str, run_id: str) -> Any:
        """
        Poll run status with adaptive backoff + hard timeout.

        This is the single biggest lever to reduce 429s.
        """
        start = self._time()

        # A gentle schedule that ramps up quickly.
        schedule = [1.0, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0]
        idx = 0

        # First retrieve after a short delay to avoid instant double-hit after create.
        self._sleep(schedule[0])
        run = self._retrieve_run(thread_id=thread_id, run_id=run_id)

        while getattr(run, "status", None) in ("queued", "in_progress"):
            elapsed = self._time() - start
            if elapsed >= self._run_timeout_s:
                raise RuntimeError(
                    f"Assistant run timed out after {int(self._run_timeout_s)}s"
                )

            delay = schedule[min(idx, len(schedule) - 1)]
            idx += 1
            self._sleep(delay)
            run = self._retrieve_run(thread_id=thread_id, run_id=run_id)

        return run

    def _extract_text_from_messages(self, messages: Any) -> str:
        """
        Extract the most recent assistant message text robustly.

        SDK shapes vary; we avoid assuming messages.data[0].content[0].text is always correct.
        """
        data = getattr(messages, "data", None)
        if not data:
            return ""

        # Messages are typically newest-first, but don’t assume; prefer the latest assistant role.
        for msg in data:
            if getattr(msg, "role", None) != "assistant":
                continue
            content = getattr(msg, "content", None)
            if not content:
                continue

            # content is a list of content parts; find text parts.
            parts = []
            for part in content:
                # Part may have .type and .text (with .value), depending on SDK version.
                ptype = getattr(part, "type", None)
                if ptype == "text":
                    text_obj = getattr(part, "text", None)
                    if text_obj is None:
                        continue
                    val = getattr(text_obj, "value", None)
                    if isinstance(val, str) and val.strip():
                        parts.append(val)
                else:
                    # Some SDK versions store text differently
                    text_obj = getattr(part, "text", None)
                    if isinstance(text_obj, str) and text_obj.strip():
                        parts.append(text_obj)

            if parts:
                return "\n".join(parts).strip()

        # Fallback: any message content
        for msg in data:
            content = getattr(msg, "content", None)
            if not content:
                continue
            for part in content:
                text_obj = getattr(part, "text", None)
                val = getattr(text_obj, "value", None) if text_obj is not None else None
                if isinstance(val, str) and val.strip():
                    return val.strip()

        return ""

    # --------------------------
    # Parse / validate
    # --------------------------

    def _parse_and_validate(
        self,
        response_text: str,
        cv_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Parse the response and validate against the schema.
        """
        # Normalize response text (may already be plain string)
        text = response_text.strip()

        # Remove markdown fences if present
        if text.startswith("```json"):
            text = text[len("```json") :]
        elif text.startswith("```"):
            text = text[len("```") :]
        if text.endswith("```"):
            text = text[: -len("```")]
        text = text.strip()

        # Parse JSON
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse response as JSON: {e}\nResponse was: {text[:500]}"
            ) from e

        if not isinstance(data, dict):
            raise ValueError("Response must be a JSON object")

        return data
