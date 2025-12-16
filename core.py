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

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple
from zipfile import ZipFile

from docxtpl import DocxTemplate
from lxml import etree

from .logging_utils import LOG

# ------------------------- XML parsing helpers -------------------------

XML_PARSER = etree.XMLParser(recover=True, huge_tree=True)

def strip_invalid_xml_1_0_chars(s: str) -> str:
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
    s = strip_invalid_xml_1_0_chars(s)
    return s

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

_WS_RE = re.compile(r"\s+")

def clean_text(text: str) -> str:
    """Collapse whitespace for clean JSON output."""
    text = normalize_text_for_processing(text)
    text = _WS_RE.sub(" ", text)
    return text.strip()

_SPLIT_RE = re.compile(r"\s*(?:,|;|\||\u2022|\u00B7|\u2027|\u2219|\u25CF)\s*|\s{2,}")

def normalize_sidebar_sections(sections: Dict[str, List[str]]) -> Dict[str, List[str]]:
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

# ------------------------- DOCX namespaces -------------------------

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

EXPECTED_SIDEBAR_SECTIONS = [
    "languages",
    "tools",
    "industries",
    "spoken_languages",
    "academic_background",
]

ENVIRONMENT_PATTERN = re.compile(
    r"^Environment\s*:\s*(.+)$",
    re.IGNORECASE,
)

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

# ------------------------- DOCX body parsing -------------------------

def extract_text_from_w_p(p: etree._Element) -> str:
    parts: List[str] = []
    for node in p.iter():
        tag = etree.QName(node).localname
        if tag == "t" and node.text:
            parts.append(node.text)
        elif tag in ("noBreakHyphen", "softHyphen"):
            parts.append("-")
        elif tag in ("br", "cr"):
            parts.append("\n")
        elif tag == "tab":
            parts.append("\t")
    return normalize_text_for_processing("".join(parts)).strip()

def _p_style(p: etree._Element) -> str:
    pstyle = p.find(".//w:pPr/w:pStyle", DOCX_NS)
    if pstyle is None:
        return ""
    return pstyle.get(f"{{{W_NS}}}val", "") or ""

def _p_is_bullet(p: etree._Element) -> bool:
    # Word list formatting is usually in <w:numPr>
    if p.find(".//w:pPr/w:numPr", DOCX_NS) is not None:
        return True
    # Some templates use paragraph styles for lists; treat common list styles as bullets
    style = _p_style(p).lower()
    if style.startswith("list") or "bullet" in style or "number" in style:
        return True
    return False

def iter_document_paragraphs(docx_path: Path) -> Iterator[Tuple[str, bool, str]]:
    """
    Yield (text, is_bullet, style) for each paragraph in word/document.xml body.
    """
    with ZipFile(docx_path) as z:
        xml_bytes = z.read("word/document.xml")
    root = etree.fromstring(xml_bytes, XML_PARSER)

    for p in root.findall(".//w:body//w:p", DOCX_NS):
        text = extract_text_from_w_p(p)
        if not text:
            continue
        yield text, _p_is_bullet(p), _p_style(p)

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

def dump_body_sample(docx_path: Path, n: int = 25) -> None:
    LOG.info("---- BODY SAMPLE ----")
    try:
        for i, (txt, is_bullet, style) in enumerate(iter_document_paragraphs(docx_path)):
            if i >= n:
                break
            flag = "•" if is_bullet else " "
            LOG.info("%02d [%s] %-14s | %s", i, flag, style[:14], txt[:160])
    except Exception as e:
        LOG.error("(failed to dump body sample: %s)", e)
    LOG.info("---------------------")

# ------------------------- Header/sidebar parsing -------------------------

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
    
    sections = normalize_sidebar_sections(sections)
    return identity, sections

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
        if not bullets:
            issue_set.add("no bullets")
        if env is not None and not isinstance(env, list):
            warnings.append("invalid environment format")

    if issue_set:
        warnings.append("incomplete: " + "; ".join(sorted(issue_set)))

    ok = not errors
    return VerificationResult(ok=ok, errors=errors, warnings=warnings)

def process_single_docx(docx_path: Path, out: Optional[Path]) -> Tuple[VerificationResult, Dict[str, Any]]:
    data = extract_cv_structure(docx_path)

    if out is None:
        out = docx_path.with_suffix(".json")

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return verify_extracted_data(data, docx_path), data

# ------------------------- Rendering -------------------------

def render_from_json(json_path: Path, template_path: Path, target_dir: Path) -> Path:
    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    data = sanitize_for_xml_in_obj(data)

    tpl = DocxTemplate(str(template_path))
    tpl.render(data, autoescape=True)

    out_docx = target_dir / f"{json_path.stem}_NEW.docx"
    tpl.save(str(out_docx))
    return out_docx