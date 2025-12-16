"""
Shared models and text utilities.

Defines common data structures (identity, experience, verification results)
and text normalization helpers used across extraction, parsing, and rendering.
"""

from __future__ import annotations

import re

from dataclasses import dataclass, field
from typing import Any, Dict, List

@dataclass(frozen=True)
class Identity:
    title: str
    full_name: str
    first_name: str
    last_name: str

    def as_dict(self) -> Dict[str, str]:
        return {
            "title": self.title,
            "full_name": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
        }

@dataclass
class ExperienceBuilder:
    heading: str = ""
    description_parts: List[str] = field(default_factory=list)
    bullets: List[str] = field(default_factory=list)
    environment: List[str] = field(default_factory=list)

    def finalize(self) -> Dict[str, Any]:
        return {
            "heading": self.heading.strip(),
            "description": " ".join(self.description_parts).strip(),
            "bullets": self.bullets[:],
            "environment": self.environment[:] or None,
        }

@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    errors: List[str]
    warnings: List[str]

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