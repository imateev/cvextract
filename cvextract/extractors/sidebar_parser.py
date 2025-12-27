"""
Header/sidebar parsing for CVs.

Extracts text from DOCX header parts and converts it into:
- identity (title + name)
- sidebar sections (skills, languages, tools, etc.)
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple
from zipfile import ZipFile

from lxml import etree
from ..logging_utils import LOG
from ..shared import (
    clean_text,
    Identity, 
)
from ..docx_utils import (
    extract_text_from_w_p,
    XML_PARSER,
)

# ------------------------- Patterns / section titles -------------------------

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
DOCX_NS = {"w": W_NS}

# include other namespaces for shapes/textboxes commonly used in headers
HEADER_NS = {
    "w": W_NS,
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
    "v": "urn:schemas-microsoft-com:vml",
    "wp": "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing",
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "w10": "urn:schemas-microsoft-com:office:word",
}

_SPLIT_RE = re.compile(r"\s*(?:,|;|\||\u2022|\u00B7|\u2027|\u2219|\u25CF)\s*|\s{2,}")

# ------------------------- Header/sidebar parsing -------------------------

# Sidebar section headings as they appear in the DOCX
SECTION_TITLES: Dict[str, str] = {
    "SKILLS": "skills",
    "LANGUAGES": "languages",
    "TOOLS": "tools",
    "CERTIFICATIONS": "certifications",
    "INDUSTRIES": "industries",
    "SPOKEN LANGUAGES": "spoken_languages",
    "ACADEMIC BACKGROUND": "academic_background",
}

# Normalize heading text (strip/clean + uppercase + trim trailing punctuation)
def _normalize_heading(text: str) -> str:
    cleaned = clean_text(text)
    return cleaned.upper().rstrip(" .:;") if cleaned else ""


def _iter_heading_positions(paragraphs: List[str]) -> List[Tuple[int, str]]:
    """Return (index, section_key) for all recognized headings."""
    positions: List[Tuple[int, str]] = []
    for i, p in enumerate(paragraphs):
        norm = _normalize_heading(p)
        key = SECTION_TITLES.get(norm)
        if key:
            positions.append((i, key))
    return positions

def _normalize_sidebar_sections(sections: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Normalize sidebar sections into clean lists.
    Splits on:
      - commas
      - 2+ spaces
    Preserves order, removes empties, de-dupes.
    """
    out: Dict[str, List[str]] = {}

    for key, lines in (sections or {}).items():
        items: List[str] = []
        seen: set[str] = set()

        for line in (lines or []):
            line = clean_text(line)
            if not line:
                continue

            parts = [clean_text(p) for p in _SPLIT_RE.split(line)]

            for p in parts:
                if not p:
                    continue
                if p not in seen:
                    seen.add(p)
                    items.append(p)

        out[key] = items

    return out

def _extract_paragraph_texts(root: etree._Element) -> List[str]:
    """
    Extract visible text paragraphs from a header XML root.
    Prefer textbox content (w:txbxContent) but fall back to direct w:p.
    Preserves line breaks inside paragraphs (w:br/w:cr) by splitting into lines.
    """
    paras: List[str] = []

    # 1) Textboxes (common for sidebars)
    for p in root.findall(".//w:txbxContent//w:p", HEADER_NS):
        s = extract_text_from_w_p(p)
        if not s:
            continue
        for ln in s.split("\n"):
            ln = ln.strip()
            if ln:
                paras.append(ln)

    # 2) Fallback: normal header paragraphs
    if not paras:
        for p in root.findall(".//w:p", HEADER_NS):
            s = extract_text_from_w_p(p)
            if not s:
                continue
            for ln in s.split("\n"):
                ln = ln.strip()
                if ln:
                    paras.append(ln)

    return paras

def extract_all_header_paragraphs(docx_path: Path) -> List[str]:
    """
    Collect header paragraphs from all header parts (word/header*.xml),
    de-duplicated while preserving order.
    """
    paragraphs: List[str] = []
    with ZipFile(docx_path) as z:
        for name in sorted(z.namelist()):
            if name.startswith("word/header") and name.endswith(".xml"):
                xml_bytes = z.read(name)
                root = etree.fromstring(xml_bytes, XML_PARSER)
                paragraphs.extend(_extract_paragraph_texts(root))

    out: List[str] = []
    seen = set()
    for p in paragraphs:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out

def split_identity_and_sidebar(paragraphs: List[str]) -> Tuple[Identity, Dict[str, List[str]]]:
    """
    Given ordered header paragraphs, split into:
      identity: title + name
      sections: sidebar blocks keyed by SECTION_TITLES mapping
    """
    sections: Dict[str, List[str]] = {v: [] for v in SECTION_TITLES.values()}

    # Locate all sidebar section headings (robust to trailing punctuation)
    heading_positions = _iter_heading_positions(paragraphs)

    first_section_idx: Optional[int] = heading_positions[0][0] if heading_positions else None
    last_section_idx: Optional[int] = heading_positions[-1][0] if heading_positions else None

    # No sidebar headings found
    if first_section_idx is None:
        identity = Identity(title="", full_name="", first_name="", last_name="")
        return identity, sections

    # Identity block:
    #  - Prefer everything before first sidebar heading
    #  - If empty, try the trailing lines after the last sidebar heading
    def _unique_lines(lines: List[str]) -> List[str]:
        out: List[str] = []
        seen = set()
        for p in lines:
            p2 = clean_text(p)
            if not p2:
                continue
            if p2 not in seen:
                seen.add(p2)
                out.append(p2)
        return out

    raw_identity_lines = _unique_lines(paragraphs[:first_section_idx])

    # If identity is at the end, take the last 3 lines (title, first, last)
    ident_tail_n = 0
    if not raw_identity_lines and last_section_idx is not None:
        trailing_all = [p for p in paragraphs[last_section_idx + 1:]]
        trailing = _unique_lines(trailing_all)
        if len(trailing) >= 3:
            raw_identity_lines = trailing[-3:]
            ident_tail_n = 3
        elif len(trailing) >= 2:
            # Fall back: assume title + full_name on one line
            raw_identity_lines = trailing[-2:]
            ident_tail_n = 2

    title = raw_identity_lines[0] if raw_identity_lines else ""
    full_name = " ".join(raw_identity_lines[1:]) if len(raw_identity_lines) > 1 else ""

    name_parts = full_name.split()
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    identity = Identity(
        title=title,
        full_name=full_name,
        first_name=first_name,
        last_name=last_name,
    )

    # Sidebar sections: only between headings (avoid trailing identity lines)
    current_key: Optional[str] = None
    seen_sections = set()

    # Parse section contents from first heading to end, but exclude identity tail if present
    end_idx_exclusive = len(paragraphs)
    if ident_tail_n:
        end_idx_exclusive = max(first_section_idx or 0, end_idx_exclusive - ident_tail_n)

    for idx, p in enumerate(paragraphs[first_section_idx:end_idx_exclusive]):
        p_clean = clean_text(p)
        if not p_clean:
            continue

        norm_heading = _normalize_heading(p_clean)
        matched_key = SECTION_TITLES.get(norm_heading)

        if matched_key:
            # If we've already seen this section heading once, treat later repeats as duplicates
            if matched_key in seen_sections:
                current_key = None
                continue

            current_key = matched_key
            seen_sections.add(matched_key)
            continue

        if current_key:
            # avoid duplicates while preserving order
            if p_clean not in sections[current_key]:
                sections[current_key].append(p_clean)
    
    sections = _normalize_sidebar_sections(sections)
    return identity, sections