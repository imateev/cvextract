import json
import re
import sys
from pathlib import Path
from typing import Iterator
from zipfile import ZipFile

from docxtpl import DocxTemplate
from lxml import etree  # pip install lxml

# ---------- helpers ----------
XML_PARSER = etree.XMLParser(recover=True, huge_tree=True)

# Escape '&' only if it is NOT already an entity like &amp; or &#123; or &#x1F;
_RAW_AMP = re.compile(r'&(?!amp;|lt;|gt;|apos;|quot;|#\d+;|#x[0-9A-Fa-f]+;)')

def escape_raw_ampersands(s: str) -> str:
    return _RAW_AMP.sub("&amp;", s)

def strip_invalid_xml_1_0_chars(s: str) -> str:
    """
    Remove characters that are invalid in XML 1.0.
    Valid chars are:
      #x9 | #xA | #xD |
      [#x20-#xD7FF] |
      [#xE000-#xFFFD] |
      [#x10000-#x10FFFF]
    """
    out = []
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

def sanitize_for_xml_in_obj(obj: object) -> object:
    def _sanitize(x: object) -> object:
        if isinstance(x, str):
            x = x.replace("\u00A0", " ")
            x = escape_raw_ampersands(x)
            return strip_invalid_xml_1_0_chars(x)
        if isinstance(x, list):
            return [_sanitize(i) for i in x]
        if isinstance(x, dict):
            return {k: _sanitize(v) for k, v in x.items()}
        return x

    return _sanitize(obj)

def clean_text(text: str) -> str:
    """Collapse whitespace (keep content as-is for manual review workflow)."""
    text = text.replace("\u00A0", " ")  # Word NBSP -> normal space
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ---------- 1. MAIN BODY via DOCX XML (no pandoc) ----------
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

DOCX_NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
}

def _p_text(p) -> str:
    """Extract visible text from a <w:p> paragraph."""
    texts = [t.text for t in p.findall(".//w:t", DOCX_NS) if t.text]
    return "".join(texts).strip()

def _p_is_bullet(p) -> bool:
    """
    Detect bullets/numbered list items in Word.
    Word stores list formatting in <w:numPr>.
    """
    return p.find(".//w:pPr/w:numPr", DOCX_NS) is not None

def _p_style(p) -> str:
    """Return paragraph style id if present (e.g. Heading1)."""
    pstyle = p.find(".//w:pPr/w:pStyle", DOCX_NS)
    if pstyle is None:
        return ""
    return pstyle.get(f"{{{DOCX_NS['w']}}}val", "") or ""

def iter_document_paragraphs(docx_path: str) -> Iterator[tuple[str, bool, str]]:
    """
    Yield tuples: (text, is_bullet, style) for each body paragraph in document.xml.
    """
    with ZipFile(docx_path) as z:
        xml_bytes = z.read("word/document.xml")
    root = etree.fromstring(xml_bytes, XML_PARSER)

    for p in root.findall(".//w:body//w:p", DOCX_NS):
        text = _p_text(p)
        if not text:
            continue
        yield text, _p_is_bullet(p), _p_style(p)

def finalize_exp(exp: dict) -> dict:
    """Finalize experience object with stable key order."""
    return {
        "heading": exp.get("heading", "").strip(),
        "description": " ".join(exp.get("description_parts", [])).strip(),
        "bullets": exp.get("bullets", []),
    }

def parse_resume_from_docx_body(docx_path: str) -> tuple[str, list[dict]]:
    """
    Parse the main body directly from DOCX.
    Returns: overview (str), experiences (list of dicts).
    """
    overview_parts = []
    experiences = []
    current_exp = None
    in_overview = False
    in_experience = False

    for raw_text, is_bullet, style in iter_document_paragraphs(docx_path):
        line = raw_text.strip()
        if not line:
            continue

        upper = line.strip(" .:").upper()

        # Strict section detection
        if upper == "OVERVIEW":
            in_overview = True
            in_experience = False
            continue
        elif upper == "PROFESSIONAL EXPERIENCE":
            in_overview = False
            in_experience = True
            continue

        if in_overview:
            overview_parts.append(clean_text(line))
            continue

        if in_experience:
            is_heading_style = style.lower().startswith("heading") and not is_bullet

            if HEADING_PATTERN.search(line) or is_heading_style:
                if current_exp:
                    experiences.append(finalize_exp(current_exp))
                current_exp = {"heading": clean_text(line),
                               "description_parts": [],
                               "bullets": []}
                continue

            if is_bullet:
                if current_exp:
                    current_exp["bullets"].append(clean_text(line))
                continue

            if current_exp:
                current_exp["description_parts"].append(clean_text(line))

    if current_exp:
        experiences.append(finalize_exp(current_exp))

    overview = " ".join(overview_parts).strip()
    return overview, experiences

def dump_body_sample(docx_path: str, n: int = 25) -> None:
    """Print a small sample of parsed body paragraphs for debugging."""
    print("---- BODY SAMPLE ----")
    try:
        for i, (txt, is_bullet, style) in enumerate(iter_document_paragraphs(docx_path)):
            if i >= n:
                break
            flag = "•" if is_bullet else " "
            print(f"{i:02d} [{flag}] {style:12s} | {txt[:160]}")
    except Exception as e:
        print(f"(failed to dump body sample: {e})")
    print("---------------------")

# ---------- 2. HEADER / SIDEBAR via XML (DOCX -> header paragraphs) ----------
NS = {
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "wps": "http://schemas.microsoft.com/office/word/2010/wordprocessingShape",
}

SECTION_TITLES = {
    "SKILLS.": "skills",
    "LANGUAGES.": "languages",
    "TOOLS.": "tools",
    "CERTIFICATIONS.": "certifications",
    "INDUSTRIES.": "industries",
    "SPOKEN LANGUAGES.": "spoken_languages",
    "ACADEMIC BACKGROUND.": "academic_background",
}

def extract_all_header_paragraphs(docx_path: str) -> list[str]:
    """
    Return a list of header paragraphs (strings), collected from all headers,
    looking specifically inside text boxes (w:txbxContent).
    """
    paragraphs = []
    with ZipFile(docx_path) as z:
        for name in sorted(z.namelist()):
            if name.startswith("word/header") and name.endswith(".xml"):
                xml_bytes = z.read(name)
                root = etree.fromstring(xml_bytes, XML_PARSER)

                # paragraphs inside text boxes
                for p in root.findall(".//w:txbxContent//w:p", NS):
                    texts = [t.text for t in p.findall(".//w:t", NS) if t.text]
                    para = "".join(texts).strip()
                    if para:
                        paragraphs.append(para)
    return paragraphs

def split_identity_and_sidebar(paragraphs: list[str]) -> tuple[dict, dict]:
    """
    paragraphs: ordered header paragraphs (strings).
    Returns:
      identity: {'title': str, 'name': str}
      sections: {'languages': [...], ...}
    """

    # 1) Find first sidebar section heading index
    first_section_idx = None
    for i, p in enumerate(paragraphs):
        if p.strip().upper() in SECTION_TITLES:
            first_section_idx = i
            break

    # Base structure for sections
    sections = {v: [] for v in SECTION_TITLES.values()}

    if first_section_idx is None:
        return {"title": "", "full_name": "", "first_name":"", "last_name":""}, sections

    # ----- Identity block: everything before first sidebar heading -----
    raw_identity_lines = []
    seen_identity = set()
    for p in paragraphs[:first_section_idx]:
        if p not in seen_identity:
            seen_identity.add(p)
            raw_identity_lines.append(p)

    if raw_identity_lines:
        title = raw_identity_lines[0]
        full_name = " ".join(raw_identity_lines[1:]) if len(raw_identity_lines) > 1 else ""
    else:
        title = ""
        full_name = ""

    name_parts = full_name.split()
    first_name = name_parts[0] if name_parts else ""
    last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""

    identity = {
        "title": title, 
        "full_name": full_name, 
        "first_name": first_name, 
        "last_name": last_name,
        }

    # ----- Sidebar sections: from first heading onward -----
    current_key = None
    seen_sections = set()

    for p in paragraphs[first_section_idx:]:
        upper = p.strip().upper()

        # If this is a section title
        if upper in SECTION_TITLES:
            key = SECTION_TITLES[upper]

            # If we've already seen this section once, assume duplicates
            if key in seen_sections:
                current_key = None
                continue

            current_key = key
            seen_sections.add(key)
            continue

        # Otherwise, content inside current section
        if current_key:
            if p not in sections[current_key]:
                sections[current_key].append(p)

    return identity, sections

# ---------- 3. High-level pipeline & CLI ----------
def extract_resume_structure(docx_path: str) -> dict:
    # Main body via DOCX XML
    overview, experiences = parse_resume_from_docx_body(docx_path)

    # Header/sidebar via XML
    header_paragraphs = extract_all_header_paragraphs(docx_path)
    identity, sidebar = split_identity_and_sidebar(header_paragraphs)

    # Build final structure
    data = {
        "identity": identity,
        "sidebar": sidebar,
        "overview": overview,
        "experiences": experiences,
    }
    return data

def verify_extracted_data(data: dict, source: Path) -> bool:
    name = source.stem
    errors = []
    warnings = []

    # --- 1. Critical checks (RED X) ---
    identity = data.get("identity", {})
    if not identity.get("title") or not identity.get("full_name") or not identity.get("first_name") or not identity.get("last_name"):
        errors.append("identity")

    sidebar = data.get("sidebar", {})
    if not any(sidebar.get(section) for section in sidebar):
        errors.append("sidebar")

    # --- Sidebar completeness check (WARNING only) ---
    expected_sidebar_sections = [
        "languages",
        "tools",
        "industries",
        "spoken_languages",
        "academic_background",
    ]

    missing_sidebar_sections = [
        section for section in expected_sidebar_sections
        if not sidebar.get(section)
    ]

    if missing_sidebar_sections:
        warnings.append(
            "missing sidebar sections: " + ", ".join(missing_sidebar_sections)
        )

    experiences = data.get("experiences", [])
    if not experiences:
        errors.append("experiences_empty")

    # --- 2. Experience completeness check (WARNING only) ---
    issue_set = set()  # collect unique issues across all experiences

    if experiences:
        for exp in experiences:
            heading = exp.get("heading", "").strip()
            desc = exp.get("description", "").strip()
            bullets = exp.get("bullets", [])

            if not heading:
                issue_set.add("missing heading")
            if not desc:
                issue_set.add("missing description")
            if not bullets:
                issue_set.add("no bullets")

    if issue_set:
        # produce a single combined warning string
        warnings.append("incomplete: " + "; ".join(sorted(issue_set)))

    # --- Output logic (one line per file) ---
    if errors:
        print(f"❌ Extracted {name} ({'; '.join(errors)})")
        return False

    if warnings:
        print(f"⚠️  Extracted {name} ({'; '.join(warnings)})")
        return True

    print(f"🟢 Extracted {name}")
    return True

def process_single_docx(docx_path: Path, out: Path | None = None) -> bool:
    """Process one .docx and write its JSON output."""
    data = extract_resume_structure(str(docx_path))
    
    if out is None:
        out = docx_path.with_suffix(".json")

    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    ok = verify_extracted_data(data, docx_path)
    return ok

# ===================== MODES =====================

def render_from_json(json_path: Path, template_path: Path, target_dir: Path) -> Path:
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    data = sanitize_for_xml_in_obj(data)

    tpl = DocxTemplate(template_path)
    tpl.render(data, autoescape=True)

    out_docx = target_dir / f"{json_path.stem}_NEW.docx"
    tpl.save(out_docx)
    return out_docx

def run_extract_mode(inputs: list[Path], target_dir: Path) -> None:
    processed = 0
    extracted_ok = 0

    for docx_file in inputs:
        if docx_file.suffix.lower() != ".docx":
            continue
        processed += 1
        try:
            out_json = target_dir / f"{docx_file.stem}.json"
            ok = process_single_docx(docx_file, out=out_json)
            if ok:
                extracted_ok += 1
        except Exception as e:
            print(f"❌ ❌ ❌ Error processing {docx_file}: {e}")
            dump_body_sample(str(docx_file), n=30)

    print(f"\n🟢 Extracted {extracted_ok} of {processed} file(s) to JSON in: {target_dir}")


def run_extract_apply_mode(inputs: list[Path], template_path: Path, target_dir: Path) -> None:
    processed = 0
    extracted_ok = 0
    rendered_ok = 0

    json_dir = target_dir / "structured_data"
    json_dir.mkdir(parents=True, exist_ok=True)

    for docx_file in inputs:
        if docx_file.suffix.lower() != ".docx":
            continue
        processed += 1
        try:
            out_json = json_dir / f"{docx_file.stem}.json"
            ok = process_single_docx(docx_file, out=out_json)
            if ok:
                extracted_ok += 1
                try:
                    out_docx = render_from_json(out_json, template_path, target_dir)
                    print(f"✅ Rendered: {out_docx.name}")
                    rendered_ok += 1
                except Exception as e:
                    print(f"❌ Failed rendering for {out_json.name}: {e}")
        except Exception as e:
            print(f"❌ ❌ ❌ Error processing {docx_file}: {e}")
            dump_body_sample(str(docx_file), n=30)

    print(
        f"\n🟢 Extracted {extracted_ok} of {processed} file(s) to JSON "
        f"and rendered {rendered_ok} DOCX file(s) into: {target_dir}"
    )


def run_apply_mode(inputs: list[Path], template_path: Path, target_dir: Path) -> None:
    processed = 0
    rendered_ok = 0

    for json_file in inputs:
        if json_file.suffix.lower() != ".json":
            continue
        processed += 1
        try:
            out_docx = render_from_json(json_file, template_path, target_dir)
            print(f"🟢 {out_docx.name}")
            rendered_ok += 1
        except Exception as e:
            print(f"❌ Failed rendering for {json_file.name}: {e}")

    print(f"\n🟢 Rendered {rendered_ok} of {processed} JSON file(s) into: {target_dir}")


# ===================== MAIN =====================

def main() -> None:
    import argparse

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

    parser.add_argument(
        "--mode",
        required=True,
        choices=["extract", "extract-apply", "apply"],
        help="Operation mode",
    )

    parser.add_argument(
        "--source",
        required=True,
        help="Input file or folder (.docx for extract*, .json for apply)",
    )

    parser.add_argument(
        "--template",
        required=True,
        help="Template .docx (single file)",
    )

    parser.add_argument(
        "--target",
        required=True,
        help="Target output directory",
    )

    args = parser.parse_args()

    mode = args.mode
    src = Path(args.source)
    template_path = Path(args.template)
    target_dir = Path(args.target)

    # --- validate template ---
    if not template_path.is_file() or template_path.suffix.lower() != ".docx":
        print(f"Template not found or not a .docx: {template_path}")
        sys.exit(1)

    # --- validate target ---
    target_dir.mkdir(parents=True, exist_ok=True)
    if not target_dir.is_dir():
        print(f"Target is not a directory: {target_dir}")
        sys.exit(1)

    # --- collect inputs ---
    if src.is_file():
        inputs = [src]
    elif src.is_dir():
        if mode in ("extract", "extract-apply"):
            inputs = [
                p for p in src.iterdir()
                if p.is_file()
                and p.suffix.lower() == ".docx"
                and p.resolve() != template_path.resolve()
            ]
        else:
            inputs = [
                p for p in src.iterdir()
                if p.is_file()
                and p.suffix.lower() == ".json"
            ]
    else:
        print(f"Path not found or not a file/folder: {src}")
        sys.exit(1)

    if not inputs:
        print("No matching input files found.")
        sys.exit(1)

    # --- dispatch ---
    if mode == "extract":
        run_extract_mode(inputs, target_dir)
    elif mode == "extract-apply":
        run_extract_apply_mode(inputs, template_path, target_dir)
    else:
        run_apply_mode(inputs, template_path, target_dir)


if __name__ == "__main__":
    main()
