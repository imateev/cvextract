"""
High-level CV extraction pipeline.

This module defines the public, end-to-end pipeline for extracting structured
data from a CV stored as a DOCX file. It orchestrates lower-level parsing
functions from `cvextract.core` and combines their outputs into a single,
validated data structure suitable for serialization or downstream processing.

Responsibilities
----------------
- Run the full extraction flow on a DOCX file:
  - parse body content (overview + experiences)
  - extract and interpret header content (identity + sidebar)
- Assemble a normalized, JSON-serializable CV structure
- Perform structural validation and consistency checks
- Provide a simple, stable API for CLI and external consumers

This module intentionally contains *no DOCX parsing logic itself*; all
document-specific parsing is delegated to lower-level logic.

Design Notes
------------
- Validation returns structured results instead of raising exceptions, allowing
  batch processing with predictable error reporting.
- Output is designed to be stable and human-readable (UTF-8, pretty-printed JSON).
- This module is intended to be the primary integration point for the CLI and
  any external consumers of `cvextract`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from .shared import VerificationResult

from .core import extract_all_header_paragraphs, split_identity_and_sidebar
from .body_parser import parse_cv_from_docx_body
# ------------------------- Constants -------------------------

EXPECTED_SIDEBAR_SECTIONS = [
    "languages",
    "tools",
    "industries",
    "spoken_languages",
    "academic_background",
]

# ------------------------- Data models -------------------------

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

# ------------------------- High-level pipeline -------------------------

def extract_cv_structure(docx_path: Path) -> Dict[str, Any]:
    overview, experiences = parse_cv_from_docx_body(docx_path)
    header_paragraphs = extract_all_header_paragraphs(docx_path)
    identity, sidebar = split_identity_and_sidebar(header_paragraphs)

    return {
        "identity": identity.as_dict(),
        "sidebar": sidebar,
        "overview": overview,
        "experiences": experiences,
    }

def process_single_docx(docx_path: Path, out: Optional[Path]) -> Tuple[VerificationResult, Dict[str, Any]]:
    data = extract_cv_structure(docx_path)

    if out is None:
        out = docx_path.with_suffix(".json")

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return verify_extracted_data(data, docx_path), data

def verify_extracted_data(data: Dict[str, Any], source: Path) -> VerificationResult:
    """
    Verify extracted data. Returns issues; does NOT log (so we can keep one log line per file).
    """
    errors: List[str] = []
    warnings: List[str] = []

    identity = data.get("identity", {}) or {}
    if not identity.get("title") or not identity.get("full_name") or not identity.get("first_name") or not identity.get("last_name"):
        errors.append("identity")

    sidebar = data.get("sidebar", {}) or {}
    if not any(sidebar.get(section) for section in sidebar):
        errors.append("sidebar")

    missing_sidebar_sections = [s for s in EXPECTED_SIDEBAR_SECTIONS if not sidebar.get(s)]
    if missing_sidebar_sections:
        warnings.append("missing sidebar: " + ", ".join(missing_sidebar_sections))

    experiences = data.get("experiences", []) or []
    if not experiences:
        errors.append("experiences_empty")

    has_any_bullets = False
    has_any_environment = False
    issue_set = set()
    for exp in experiences:
        heading = (exp.get("heading") or "").strip()
        desc = (exp.get("description") or "").strip()
        bullets = exp.get("bullets") or []
        env = exp.get("environment")
        if not heading:
            issue_set.add("missing heading")
        if not desc:
            issue_set.add("missing description")
        if bullets:
            has_any_bullets = True
        if env:
            has_any_environment = True
        if env is not None and not isinstance(env, list):
            warnings.append("invalid environment format")

    if not has_any_bullets and not has_any_environment:
        warnings.append("no bullets or environment in any experience")

    if issue_set:
        warnings.append("incomplete: " + "; ".join(sorted(issue_set)))

    ok = not errors
    return VerificationResult(ok=ok, errors=errors, warnings=warnings)