"""
Parse the main body of a CV from a DOCX file.

This module interprets paragraph-level text extracted from Word and converts
it into structured CV data:
- overview text
- professional experience entries (heading, description, bullets, environment)

Low-level DOCX/XML parsing is handled elsewhere; this module focuses only on
CV-specific structure and rules.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from lxml import etree
from ..shared import (
    clean_text,
    ExperienceBuilder,
)
from .docx_utils import (
    iter_document_paragraphs,
)

# ------------------------- Patterns / section titles -------------------------

MONTH_NAME = (
    r"(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|"
    r"May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|"
    r"Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)

HEADING_PATTERN = re.compile(
    rf"{MONTH_NAME}\s+\d{{4}}\s*"
    r"(?:--|[-–—])\s*"
    rf"(?:Present|Now|Current|{MONTH_NAME}\s+\d{{4}})",
    re.IGNORECASE,
)

ENVIRONMENT_PATTERN = re.compile(
    r"^Environment\s*:\s*(.+)$",
    re.IGNORECASE,
)

def parse_cv_from_docx_body(docx_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Parse the main body directly from DOCX.
    Returns: overview (str), experiences (list of dicts).
    """
    overview_parts: List[str] = []
    experiences: List[Dict[str, Any]] = []

    current_exp: Optional[ExperienceBuilder] = None
    in_overview = False
    in_experience = False

    def flush_current() -> None:
        nonlocal current_exp
        if current_exp is not None:
            experiences.append(current_exp.finalize())
            current_exp = None

    for raw_text, is_bullet, style in iter_document_paragraphs(docx_path):
        line = raw_text.strip()
        if not line:
            continue

        upper = line.strip(" .:").upper()

        # Strict section detection
        if upper == "OVERVIEW":
            flush_current()
            in_overview = True
            in_experience = False
            continue
        if upper == "PROFESSIONAL EXPERIENCE":
            flush_current()
            in_overview = False
            in_experience = True
            continue

        if in_overview:
            overview_parts.append(clean_text(line))
            continue

        if in_experience:
            # Heading detection: either matches date range OR is a heading style
            is_heading_style = (style.lower().startswith("heading") and not is_bullet)
            if HEADING_PATTERN.search(line) or is_heading_style:
                flush_current()
                current_exp = ExperienceBuilder(heading=clean_text(line))
                continue

            m_env = ENVIRONMENT_PATTERN.match(line)
            if m_env and current_exp is not None:
                techs_raw = m_env.group(1)
                techs = [clean_text(t) for t in techs_raw.split(",") if clean_text(t)]
                current_exp.environment.extend(techs)
                continue

            if is_bullet:
                if current_exp is not None:
                    current_exp.bullets.append(clean_text(line))
                continue

            if current_exp is not None:
                current_exp.description_parts.append(clean_text(line))

    flush_current()
    overview = " ".join(overview_parts).strip()
    return overview, experiences