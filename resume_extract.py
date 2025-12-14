#!/usr/bin/env python3
"""
resume_extract.py

A command-line tool that converts résumé/CV .docx files into a clean, structured JSON format and can optionally generate a new .docx by filling a Word template with that JSON.

What it does
- Reads a .docx directly from its WordprocessingML (XML) parts to extract content reliably without external converters.
- Produces a consistent JSON structure containing:
  - identity: title, full name, first name, last name (from the document header)
  - sidebar: categorized lists such as skills, languages, tools, certifications, industries, spoken languages, and academic background (from header/sidebar text boxes)
  - overview: free-text overview section (from the main document body)
  - experiences: a list of experience entries, each with a heading, description, and bullet points (from the main document body)

Core functions / modes
- extract:
  - Scans one .docx or a folder of .docx files and writes one JSON file per résumé.
- extract-apply:
  - Extracts JSON as above, then renders a new .docx for each input by applying a docxtpl template.
- apply:
  - Takes existing JSON files and renders new .docx files using a docxtpl template.

How it achieves this
- DOCX parsing:
  - Opens the .docx as a ZIP archive and parses:
    - word/document.xml for the main body paragraphs, including list detection via Word numbering properties.
    - word/header*.xml for header/sidebar content, prioritizing text inside text boxes (w:txbxContent), which is where sidebar layouts are typically stored.
- Section recognition:
  - Identifies “OVERVIEW” and “PROFESSIONAL EXPERIENCE” in the body to route content into the right fields.
  - Detects experience entry boundaries using date-range headings (e.g., “Jan 2020 – Present”) and/or Word heading styles.
  - Collects bullets and description text under each experience entry based on Word list formatting and paragraph grouping.
- Safe template rendering:
  - Sanitizes extracted strings to be XML-safe (handles raw ampersands, non-breaking spaces, and invalid XML 1.0 characters) before rendering.
  - Renders with docxtpl using auto-escaping and writes the output .docx to the target directory.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple
from zipfile import ZipFile

from docxtpl import DocxTemplate
from lxml import etree

# ------------------------- Logging -------------------------

# Remap level names

LOG = logging.getLogger("resume_extract")

def setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
    )

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

    def finalize(self) -> Dict[str, Any]:
        return {
            "heading": self.heading.strip(),
            "description": " ".join(self.description_parts).strip(),
            "bullets": self.bullets[:],
        }

# ------------------------- DOCX body parsing -------------------------

def _p_text(p: etree._Element) -> str:
    """
    Extract visible text from a <w:p> paragraph, including special Word hyphen nodes.
    """
    parts: List[str] = []
    for node in p.iter():
        tag = etree.QName(node).localname

        if tag == "t" and node.text:
            parts.append(node.text)
        elif tag in ("noBreakHyphen", "softHyphen"):
            parts.append("-")  # preserve high-quality style hyphens
        elif tag in ("br", "cr"):
            parts.append("\n")
        elif tag == "tab":
            parts.append("\t")

    return normalize_text_for_processing("".join(parts)).strip()
    
def _p_is_bullet(p: etree._Element) -> bool:
    # Word list formatting is usually in <w:numPr>
    if p.find(".//w:pPr/w:numPr", DOCX_NS) is not None:
        return True
    # Some templates use paragraph styles for lists; treat common list styles as bullets
    style = _p_style(p).lower()
    if style.startswith("list") or "bullet" in style or "number" in style:
        return True
    return False

def _p_style(p: etree._Element) -> str:
    pstyle = p.find(".//w:pPr/w:pStyle", DOCX_NS)
    if pstyle is None:
        return ""
    return pstyle.get(f"{{{W_NS}}}val", "") or ""

def iter_document_paragraphs(docx_path: Path) -> Iterator[Tuple[str, bool, str]]:
    """
    Yield (text, is_bullet, style) for each paragraph in word/document.xml body.
    """
    with ZipFile(docx_path) as z:
        xml_bytes = z.read("word/document.xml")
    root = etree.fromstring(xml_bytes, XML_PARSER)

    for p in root.findall(".//w:body//w:p", DOCX_NS):
        text = _p_text(p)
        if not text:
            continue
        yield text, _p_is_bullet(p), _p_style(p)

def parse_resume_from_docx_body(docx_path: Path) -> Tuple[str, List[Dict[str, Any]]]:
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
        s = _p_text(p)
        if not s:
            continue
        for ln in s.split("\n"):
            ln = ln.strip()
            if ln:
                paras.append(ln)

    # 2) Fallback: normal header paragraphs
    # This is more speculative and breaks things if it is evalued to true for now
    if not paras:
        for p in root.findall(".//w:p", HEADER_NS):
            s = _p_text(p)
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

    # Base structure for sections
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

    return identity, sections

# ------------------------- High-level pipeline -------------------------

def extract_resume_structure(docx_path: Path) -> Dict[str, Any]:
    overview, experiences = parse_resume_from_docx_body(docx_path)
    header_paragraphs = extract_all_header_paragraphs(docx_path)
    identity, sidebar = split_identity_and_sidebar(header_paragraphs)

    return {
        "identity": identity.as_dict(),
        "sidebar": sidebar,
        "overview": overview,
        "experiences": experiences,
    }

@dataclass(frozen=True)
class VerificationResult:
    ok: bool
    errors: List[str]
    warnings: List[str]

def verify_extracted_data(data: Dict[str, Any], source: Path) -> VerificationResult:
    name = source.stem
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
        warnings.append("missing sidebar sections: " + ", ".join(missing_sidebar_sections))

    experiences = data.get("experiences", []) or []
    if not experiences:
        errors.append("experiences_empty")

    issue_set = set()
    for exp in experiences:
        heading = (exp.get("heading") or "").strip()
        desc = (exp.get("description") or "").strip()
        bullets = exp.get("bullets") or []
        if not heading:
            issue_set.add("missing heading")
        if not desc:
            issue_set.add("missing description")
        if not bullets:
            issue_set.add("no bullets")

    if issue_set:
        warnings.append("incomplete: " + "; ".join(sorted(issue_set)))

    if errors:
        LOG.error("❌ Extracted %s (%s)", name, "; ".join(errors))
        return VerificationResult(False, errors, warnings)

    if warnings:
        LOG.warning("⚠️  Extracted %s (%s)", name, "; ".join(warnings))
        return VerificationResult(True, errors, warnings)

    LOG.info("🟢 Extracted %s", name)
    return VerificationResult(True, errors, warnings)

def process_single_docx(docx_path: Path, out: Optional[Path]) -> VerificationResult:
    data = extract_resume_structure(docx_path)

    if out is None:
        out = docx_path.with_suffix(".json")

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return verify_extracted_data(data, docx_path)

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

# ------------------------- Modes -------------------------

def run_extract_mode(inputs: List[Path], target_dir: Path, strict: bool, debug: bool) -> int:
    processed = 0
    extracted_ok = 0
    had_warning = False

    for docx_file in inputs:
        if docx_file.suffix.lower() != ".docx":
            continue
        processed += 1
        try:
            out_json = target_dir / f"{docx_file.stem}.json"
            result = process_single_docx(docx_file, out=out_json)
            if result.ok:
                extracted_ok += 1
            if result.warnings:
                had_warning = True
        except Exception as e:
            LOG.error("❌ ❌ ❌ Error processing %s: %s", docx_file.name, e)
            if debug:
                LOG.error(traceback.format_exc())
            dump_body_sample(docx_file, n=30)

    LOG.info("")
    LOG.info("🟢 Extracted %d of %d file(s) to JSON in: %s", extracted_ok, processed, target_dir)

    if strict and had_warning:
        LOG.error("Strict mode enabled: warnings treated as failure.")
        return 2
    return 0 if extracted_ok == processed else 1

def run_extract_apply_mode(inputs: List[Path], template_path: Path, target_dir: Path, strict: bool, debug: bool) -> int:
    processed = 0
    extracted_ok = 0
    rendered_ok = 0
    had_warning = False

    json_dir = target_dir / "structured_data"
    json_dir.mkdir(parents=True, exist_ok=True)

    for docx_file in inputs:
        if docx_file.suffix.lower() != ".docx":
            continue
        processed += 1
        try:
            out_json = json_dir / f"{docx_file.stem}.json"
            result = process_single_docx(docx_file, out=out_json)
            if result.ok:
                extracted_ok += 1
                if result.warnings:
                    had_warning = True
                try:
                    out_docx = render_from_json(out_json, template_path, target_dir)
                    LOG.info("✅ Rendered: %s", out_docx.name)
                    rendered_ok += 1
                except Exception as e:
                    LOG.error("❌ Failed rendering for %s: %s", out_json.name, e)
                    if debug:
                        LOG.error(traceback.format_exc())
            else:
                if result.warnings:
                    had_warning = True
        except Exception as e:
            LOG.error("❌ ❌ ❌ Error processing %s: %s", docx_file.name, e)
            if debug:
                LOG.error(traceback.format_exc())
            dump_body_sample(docx_file, n=30)

    LOG.info("")
    LOG.info(
        "🟢 Extracted %d of %d file(s) to JSON and rendered %d DOCX file(s) into: %s",
        extracted_ok,
        processed,
        rendered_ok,
        target_dir,
    )

    if strict and had_warning:
        LOG.error("Strict mode enabled: warnings treated as failure.")
        return 2
    return 0 if (extracted_ok == processed and rendered_ok == extracted_ok) else 1

def run_apply_mode(inputs: List[Path], template_path: Path, target_dir: Path, debug: bool) -> int:
    processed = 0
    rendered_ok = 0

    for json_file in inputs:
        if json_file.suffix.lower() != ".json":
            continue
        processed += 1
        try:
            out_docx = render_from_json(json_file, template_path, target_dir)
            LOG.info("🟢 %s", out_docx.name)
            rendered_ok += 1
        except Exception as e:
            LOG.error("❌ Failed rendering for %s: %s", json_file.name, e)
            if debug:
                LOG.error(traceback.format_exc())

    LOG.info("")
    LOG.info("🟢 Rendered %d of %d JSON file(s) into: %s", rendered_ok, processed, target_dir)
    return 0 if rendered_ok == processed else 1

# ------------------------- CLI / main -------------------------

def collect_inputs(src: Path, mode: str, template_path: Path) -> List[Path]:
    if src.is_file():
        return [src]

    if not src.is_dir():
        raise FileNotFoundError(f"Path not found or not a file/folder: {src}")

    if mode in ("extract", "extract-apply"):
        return [
            p for p in src.iterdir()
            if p.is_file()
            and p.suffix.lower() == ".docx"
            and p.resolve() != template_path.resolve()
        ]

    return [p for p in src.iterdir() if p.is_file() and p.suffix.lower() == ".json"]

def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract CV data to JSON and optionally apply a DOCX template.",
        epilog="""
Examples:
  Extract DOCX files to JSON only:
    python resume_extract.py --mode extract --source cvs/ --template template.docx --target output/

  Extract DOCX files and apply template:
    python resume_extract.py --mode extract-apply --source cvs/ --template template.docx --target output/

  Apply template to existing JSON files:
    python resume_extract.py --mode apply --source extracted_json/ --template template.docx --target output/
""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--mode", required=True, choices=["extract", "extract-apply", "apply"], help="Operation mode")
    parser.add_argument("--source", required=True, help="Input file or folder (.docx for extract*, .json for apply)")
    parser.add_argument("--template", required=True, help="Template .docx (single file)")
    parser.add_argument("--target", required=True, help="Target output directory")

    parser.add_argument("--strict", action="store_true", help="Treat warnings as failure (non-zero exit code).")
    parser.add_argument("--debug", action="store_true", help="Verbose logs + stack traces on failure.")

    return parser.parse_args(argv)

def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)
    setup_logging(args.debug)

    mode: str = args.mode
    src = Path(args.source)
    template_path = Path(args.template)
    target_dir = Path(args.target)

    # Validate template
    if not template_path.is_file() or template_path.suffix.lower() != ".docx":
        LOG.error("Template not found or not a .docx: %s", template_path)
        return 1

    # Validate target
    target_dir.mkdir(parents=True, exist_ok=True)
    if not target_dir.is_dir():
        LOG.error("Target is not a directory: %s", target_dir)
        return 1

    # Collect inputs
    try:
        inputs = collect_inputs(src, mode, template_path)
    except Exception as e:
        LOG.error(str(e))
        if args.debug:
            LOG.error(traceback.format_exc())
        return 1

    if not inputs:
        LOG.error("No matching input files found.")
        return 1

    # Dispatch
    if mode == "extract":
        return run_extract_mode(inputs, target_dir, strict=args.strict, debug=args.debug)
    if mode == "extract-apply":
        return run_extract_apply_mode(inputs, template_path, target_dir, strict=args.strict, debug=args.debug)
    return run_apply_mode(inputs, template_path, target_dir, debug=args.debug)

if __name__ == "__main__":
    raise SystemExit(main())
