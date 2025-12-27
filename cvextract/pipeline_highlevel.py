"""
High-level CV extraction pipeline.

Orchestrates body parsing and sidebar parsing to produce a complete,
structured representation of a CV.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from .extractors import DocxCVExtractor
# ------------------------- Constants -------------------------

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
    
# ------------------------- High-level pipeline -------------------------

def extract_cv_structure(docx_path: Path) -> Dict[str, Any]:
    """
    Extract CV structure from a DOCX file using the default extractor.
    
    This function maintains backward compatibility while using the new
    pluggable extractor architecture.
    """
    extractor = DocxCVExtractor()
    return extractor.extract(docx_path)

def process_single_docx(docx_path: Path, out: Optional[Path] = None) -> Dict[str, Any]:
    """Extract CV structure and optionally write to JSON. Returns extracted data dict."""
    data = extract_cv_structure(docx_path)

    if out is not None:
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    return data