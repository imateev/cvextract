"""
Shared models and text utilities.

Defines common data structures (identity, experience, verification results)
and text normalization helpers used across extraction, parsing, and rendering.
"""

from __future__ import annotations

import re

from dataclasses import dataclass, field
from typing import Any, List, TYPE_CHECKING
from pathlib import Path
from typing import Optional

if TYPE_CHECKING:
    from .cli_config import UserConfig

# ------------------------- Models -------------------------
@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    errors: List[str]
    warnings: List[str]


@dataclass(frozen=True)
class UnitOfWork:
    """
    Container for extraction inputs and outputs.

    initial_input preserves the original input path before adjustments.
    input/output represent the current step's paths.
    """
    config: "UserConfig"
    initial_input: Optional[Path] = None
    input: Path
    output: Path
    extract_ok: Optional[bool] = None
    extract_errs: List[str] = field(default_factory=list)
    extract_warns: List[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.initial_input is None:
            object.__setattr__(self, "initial_input", self.input)

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
        except Exception:
            return None
    
    # Try adjuster prompts folder
    adjuster_prompt_path = _ADJUSTER_PROMPTS_DIR / f"{prompt_name}.md"
    if adjuster_prompt_path.exists():
        try:
            return adjuster_prompt_path.read_text(encoding="utf-8")
        except Exception:
            return None
    
    # Fall back to ml_adjustment prompts folder
    ml_prompt_path = _ML_PROMPTS_DIR / f"{prompt_name}.md"
    try:
        return ml_prompt_path.read_text(encoding="utf-8")
    except Exception:
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
    except Exception:
        return None
