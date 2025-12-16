"""
cvextract.py

Core extraction and rendering logic for the cvextract package.

This module contains the low-level, reusable functionality to:
- Parse résumé/CV .docx files directly from their WordprocessingML (XML) parts
- Normalize and sanitize extracted text for safe downstream processing
- Identify and extract structured CV sections:
  - identity (title, full name, first name, last name)
  - sidebar sections (skills, languages, tools, certifications, etc.)
  - overview text
  - professional experience entries (heading, description, bullets, environment)
- Convert extracted content into a clean, neutral JSON-compatible structure
- Render new .docx documents from structured JSON using docxtpl templates
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple
from zipfile import ZipFile

from lxml import etree
from .logging_utils import LOG
from .shared import (
    clean_text,
    Identity, 
    ExperienceBuilder,
)
from .docx_utils import (
    iter_document_paragraphs,
    extract_text_from_w_p,
)

XML_PARSER = etree.XMLParser(recover=True, huge_tree=True)

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

_SPLIT_RE = re.compile(r"\s*(?:,|;|\||\u2022|\u00B7|\u2027|\u2219|\u25CF)\s*|\s{2,}")

# ------------------------- Header/sidebar parsing -------------------------

# Sidebar section headings as they appear in the DOCX
SECTION_TITLES: Dict[str, str] = {
    "SKILLS.": "skills",
    "LANGUAGES.": "languages",
    "TOOLS.": "tools",
    "CERTIFICATIONS.": "certifications",
    "INDUSTRIES.": "industries",
    "SPOKEN LANGUAGES.": "spoken_languages",
    "ACADEMIC BACKGROUND.": "academic_background",
}

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

    # Locate first sidebar section heading
    first_section_idx: Optional[int] = None
    for i, p in enumerate(paragraphs):
        if p.strip().upper() in SECTION_TITLES:
            first_section_idx = i
            break

    # No sidebar headings found
    if first_section_idx is None:
        identity = Identity(title="", full_name="", first_name="", last_name="")
        return identity, sections

    # Identity block: everything before first sidebar heading; de-dup while preserving order
    raw_identity_lines: List[str] = []
    seen = set()
    for p in paragraphs[:first_section_idx]:
        p2 = clean_text(p)
        if not p2:
            continue
        if p2 not in seen:
            seen.add(p2)
            raw_identity_lines.append(p2)

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

    # Sidebar sections: from first heading onward
    current_key: Optional[str] = None
    seen_sections = set()

    for p in paragraphs[first_section_idx:]:
        p_clean = clean_text(p)
        if not p_clean:
            continue

        upper = p_clean.upper()

        if upper in SECTION_TITLES:
            key = SECTION_TITLES[upper]

            # If we've already seen this section heading once, treat later repeats as duplicates
            if key in seen_sections:
                current_key = None
                continue

            current_key = key
            seen_sections.add(key)
            continue

        if current_key:
            # avoid duplicates while preserving order
            if p_clean not in sections[current_key]:
                sections[current_key].append(p_clean)
    
    sections = _normalize_sidebar_sections(sections)
    return identity, sections