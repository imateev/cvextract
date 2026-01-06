"""
Shared models and text utilities.

Defines common data structures (identity, experience, verification results)
and text normalization helpers used across extraction, parsing, and rendering.
"""

from __future__ import annotations

import hashlib
import re

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, TYPE_CHECKING
from pathlib import Path
from typing import Optional

if TYPE_CHECKING:
    from .cli_config import UserConfig

from .logging_utils import LOG, fmt_issues

# ------------------------- Models -------------------------
@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    errors: List[str]
    warnings: List[str]


@dataclass
class UnitOfWork:
    """
    Container for extraction inputs and outputs.

    initial_input preserves the original input path before adjustments.
    input/output represent the current step's paths.
    """
    config: "UserConfig"
    input: Path
    output: Path
    initial_input: Optional[Path] = None
    step_statuses: Dict["StepName", "StepStatus"] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.initial_input is None:
            self.initial_input = self.input

    def _get_step_status(self, step: "StepName") -> "StepStatus":
        status = self.step_statuses.get(step)
        if status is None:
            status = StepStatus(step=step)
            self.step_statuses[step] = status
        return status

    def add_warning(self, step: "StepName", message: str) -> None:
        status = self._get_step_status(step)
        status.warnings.append(message)

    def add_error(self, step: "StepName", message: str) -> None:
        status = self._get_step_status(step)
        status.errors.append(message)

    def ensure_path_exists(
        self,
        step: "StepName",
        path: Optional[Path],
        label: str,
        must_be_file: bool = False,
    ) -> bool:
        if path is None:
            self.add_error(step, f"{label} is not set")
            return False
        if not path.exists():
            self.add_error(step, f"{label} not found: {path}")
            return False
        if must_be_file and not path.is_file():
            self.add_error(step, f"{label} is not a file: {path}")
            return False
        return True

    def has_no_errors(self, step: Optional["StepName"] = None) -> bool:
        if step is None:
            return all(not status.errors for status in self.step_statuses.values())
        status = self.step_statuses.get(step)
        return not status.errors if status else True

    def has_no_warnings_or_errors(self, step: Optional["StepName"] = None) -> bool:
        if step is None:
            return all((not status.errors and not status.warnings) for status in self.step_statuses.values())
        status = self.step_statuses.get(step)
        if status is None:
            return True
        return not status.errors and not status.warnings


class StepName(str, Enum):
    Extract = "Extract"
    Adjust = "Adjust"
    Verify = "Verify"
    Render = "Render"


@dataclass
class StepStatus:
    step: StepName
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    ConfiguredExecutorAvailable: bool = True

    @property
    def ok(self) -> bool:
        return not self.warnings and not self.errors


def get_status_icons(work: "UnitOfWork") -> Dict["StepName", str]:
    """Generate status icons for pipeline steps based on UnitOfWork statuses."""
    def icon_for(step_name: StepName) -> str:
        status = work.step_statuses.get(step_name)

        if status is None:
            return "➖"

        if step_name == StepName.Verify:
            if status.errors or status.warnings:
                return "⚠️ "
            return "✅"

        if step_name == StepName.Render:
            if status.errors:
                return "❌"
            if status.warnings:
                return "⚠️ "
            verify_status = work.step_statuses.get(StepName.Verify)
            if verify_status and verify_status.errors:
                return "❌"
            return "✅"

        if status.errors:
            return "❌"
        if status.warnings:
            return "⚠️ "
        if step_name == StepName.Extract:
            return "🟢"
        return "✅"

    return {step_name: icon_for(step_name) for step_name in StepName}

def select_issue_step(work: "UnitOfWork") -> "StepName":
    for candidate in (StepName.Verify, StepName.Render, StepName.Adjust, StepName.Extract):
        status = work.step_statuses.get(candidate)
        if status and (status.errors or status.warnings):
            return candidate
    return StepName.Extract


def emit_work_status(work: "UnitOfWork", step: Optional["StepName"] = None) -> str:
    icons = get_status_icons(work)
    issue_step = step
    if issue_step is None:
        issue_step = select_issue_step(work)
    input_path = work.initial_input or work.input
    return (
        f"{icons[StepName.Extract]}"
        f"{icons[StepName.Render]}"
        f"{icons[StepName.Verify]} "
        f"{input_path.name} | "
        f"{fmt_issues(work, issue_step)}"
    )


def emit_summary(work: "UnitOfWork") -> str:
    config = work.config
    if config.extract and config.render:
        return (
            "📊 Extract+Render complete. JSON: %s | DOCX: %s"
            % (config.workspace.json_dir, config.workspace.documents_dir)
        )
    if config.extract:
        return "📊 Extract complete. JSON in: %s" % config.workspace.json_dir
    return "📊 Render complete. Output in: %s" % config.workspace.documents_dir

# ------------------------- XML parsing helpers -------------------------

_WS_RE = re.compile(r"\s+")

def _strip_invalid_xml_1_0_chars(s: str) -> str:
    """
    Remove characters invalid in XML 1.0.
    Valid:
      #x9 | #xA | #xD |
      [#x20-#xD7FF] |
      [#xE000-#xFFFD] |
      [#x10000-#x10FFFF]
    """
    out: List[str] = []
    for ch in s:
        cp = ord(ch)
        if (
            cp == 0x9
            or cp == 0xA
            or cp == 0xD
            or (0x20 <= cp <= 0xD7FF)
            or (0xE000 <= cp <= 0xFFFD)
            or (0x10000 <= cp <= 0x10FFFF)
        ):
            out.append(ch)
    return "".join(out)

def normalize_text_for_processing(s: str) -> str:
    """
    Normalize what we consider "text":
    - convert NBSP to normal space
    - replace soft hyphen with real hyphen
    - normalize newlines
    - strip invalid XML chars
    """
    s = s.replace("\u00A0", " ")
    s = s.replace("\u00AD", "-")  # preserve "high-quality"
    s = s.replace("\r\n", "\n").replace("\r", "\n")
    s = _strip_invalid_xml_1_0_chars(s)
    return s

def clean_text(text: str) -> str:
    """Collapse whitespace for clean JSON output."""
    text = normalize_text_for_processing(text)
    text = _WS_RE.sub(" ", text)
    return text.strip()

def sanitize_for_xml_in_obj(obj: Any) -> Any:
    """
    Sanitize strings for insertion into docxtpl (XML-safe):
    - normalize NBSP
    - strip invalid XML 1.0 chars
    """
    def _sanitize(x: Any) -> Any:
        if isinstance(x, str):
            x = normalize_text_for_processing(x)
            return x
        if isinstance(x, list):
            return [_sanitize(i) for i in x]
        if isinstance(x, dict):
            return {k: _sanitize(v) for k, v in x.items()}
        return x
    return _sanitize(obj)


def url_to_cache_filename(url: str) -> str:
    """
    Convert a URL to a safe, deterministic filename for caching.

    Returns:
        "example.com-abc123.research.json"
    """
    domain = re.sub(r"^https?://", "", url.lower())
    domain = re.sub(r"^www\.", "", domain)
    domain = domain.split("/")[0].split("?")[0].split("#")[0]
    domain = domain.split(":")[0]

    url_hash = hashlib.md5(url.lower().encode()).hexdigest()[:8]
    safe_domain = re.sub(r"[^a-z0-9.-]", "_", domain)
    return f"{safe_domain}-{url_hash}.research.json"


# ---------------------- Prompt Loading ----------------------

# Paths to prompts directories
_EXTRACTOR_PROMPTS_DIR = Path(__file__).parent / "extractors" / "prompts"
_ADJUSTER_PROMPTS_DIR = Path(__file__).parent / "adjusters" / "prompts"
_ML_PROMPTS_DIR = Path(__file__).parent / "ml_adjustment" / "prompts"


def load_prompt(prompt_name: str) -> Optional[str]:
    """
    Load a prompt template from a Markdown file.
    
    Searches in this order:
    1. Extractor prompts folder: cvextract/extractors/prompts/{prompt_name}.md
    2. Adjuster prompts folder: cvextract/adjusters/prompts/{prompt_name}.md
    3. ML adjustment prompts folder: cvextract/ml_adjustment/prompts/{prompt_name}.md
    
    Args:
        prompt_name: Name of the prompt file (without .md extension)
    
    Returns:
        The prompt text, or None if the file doesn't exist or can't be read
    
    Example:
        >>> cv_system = load_prompt("cv_extraction_system")
        >>> if cv_system:
        ...     print(cv_system[:50])
    """
    # Try extractor prompts folder first
    extractor_prompt_path = _EXTRACTOR_PROMPTS_DIR / f"{prompt_name}.md"
    if extractor_prompt_path.exists():
        try:
            return extractor_prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            LOG.error("Failed to read prompt %s: %s", extractor_prompt_path, e)
            return None
    
    # Try adjuster prompts folder
    adjuster_prompt_path = _ADJUSTER_PROMPTS_DIR / f"{prompt_name}.md"
    if adjuster_prompt_path.exists():
        try:
            return adjuster_prompt_path.read_text(encoding="utf-8")
        except Exception as e:
            LOG.error("Failed to read prompt %s: %s", adjuster_prompt_path, e)
            return None
    
    # Fall back to ml_adjustment prompts folder
    ml_prompt_path = _ML_PROMPTS_DIR / f"{prompt_name}.md"
    try:
        return ml_prompt_path.read_text(encoding="utf-8")
    except Exception as e:
        LOG.error("Failed to read prompt %s: %s", ml_prompt_path, e)
        return None


def format_prompt(prompt_name: str, **kwargs) -> Optional[str]:
    """
    Load a prompt template and format it with the provided variables.
    
    Args:
        prompt_name: Name of the prompt file (without .md extension)
        **kwargs: Variables to substitute in the prompt template
    
    Returns:
        The formatted prompt text, or None if the file doesn't exist or can't be read
    
    Example:
        >>> prompt = format_prompt("website_analysis_prompt", 
        ...                        customer_url="https://example.com",
        ...                        schema="{}")
        >>> if prompt:
        ...     print(prompt[:50])
    """
    template = load_prompt(prompt_name)
    if template is None:
        return None
    
    try:
        return template.format(**kwargs)
    except Exception as e:
        LOG.error("Failed to format prompt %s: %s", prompt_name, e)
        return None
