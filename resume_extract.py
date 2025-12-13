import re
import json
import subprocess
from zipfile import ZipFile
from lxml import etree  # pip install lxml
from docxtpl import DocxTemplate
import sys
from pathlib import Path

# ---------- helpers ----------

# Escape '&' only if it is NOT already an entity like &amp; or &#123; or &#x1F;
_RAW_AMP = re.compile(r'&(?!amp;|lt;|gt;|apos;|quot;|#\d+;|#x[0-9A-Fa-f]+;)')

def escape_raw_ampersands(s: str) -> str:
    return _RAW_AMP.sub("&amp;", s)

def escape_raw_ampersands_in_obj(obj):
    """Recursively escape raw ampersands in strings inside dict/list structures."""
    if isinstance(obj, str):
        return escape_raw_ampersands(obj)
    if isinstance(obj, list):
        return [escape_raw_ampersands_in_obj(x) for x in obj]
    if isinstance(obj, dict):
        return {k: escape_raw_ampersands_in_obj(v) for k, v in obj.items()}
    return obj

_invalid_xml_chars = re.compile(
    r"[^\x09\x0A\x0D\x20-\uD7FF\uE000-\uFFFD]"
)

def contains_bad_xml_chars(s: str) -> bool:
    return bool(_invalid_xml_chars.search(s))

def scan_data_for_bad_chars(obj, path="root"):
    hits = []
    if isinstance(obj, str):
        if contains_bad_xml_chars(obj):
            hits.append((path, repr(obj[:200])))
    elif isinstance(obj, list):
        for i, x in enumerate(obj):
            hits += scan_data_for_bad_chars(x, f"{path}[{i}]")
    elif isinstance(obj, dict):
        for k, v in obj.items():
            hits += scan_data_for_bad_chars(v, f"{path}.{k}")
    return hits

def clean_text(text: str) -> str:
    """Remove unwanted characters like *, > and collapse spaces."""
    text = re.sub(r"[*>\\]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ---------- 1. MAIN BODY via pandoc (DOCX -> Markdown -> parsed) ----------
def run_pandoc_to_markdown(docx_path: str) -> str:
    """
    Call pandoc to convert DOCX to Markdown and return the markdown text.
    Requires pandoc installed and on PATH.
    """
    result = subprocess.run(
        [
            "pandoc",
            docx_path,
            "-t", "markdown",
            "--wrap=none",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(f"pandoc failed: {result.stderr}")

    return result.stdout

def parse_resume_markdown(md_text: str):
    """
    Parse the markdown text from the main body.
    Returns: overview (str), experiences (list of dicts).
    """
    overview = ""
    experiences = []
    current_exp = None
    in_overview = False
    in_experience = False

    lines = [
        line for line in md_text.splitlines()
        if line.strip() != "" and not all(ch == ">" for ch in line.strip())
    ]

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

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        upper = line.upper()

        # Detect sections
        if "OVERVIEW" in upper:
            in_overview = True
            in_experience = False
            continue
        elif "PROFESSIONAL EXPERIENCE" in upper:
            in_overview = False
            in_experience = True
            continue

        # Capture Overview text
        if in_overview:
            overview += clean_text(line) + " "
            continue

        # Capture Experience entries
        if in_experience:
            # Detect new job heading (date range + title) by month name
            if HEADING_PATTERN.search(line):
                if current_exp:
                    experiences.append(current_exp)
                current_exp = {"heading": clean_text(line),
                               "description": "",
                               "bullets": []}
            elif line.startswith("-"):
                if current_exp:
                    bullet_text = clean_text(line.lstrip("- ").strip())
                    current_exp["bullets"].append(bullet_text)
            else:
                if current_exp:
                    current_exp["description"] += clean_text(line) + " "

    if current_exp:
        experiences.append(current_exp)

    return overview.strip(), experiences

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

def extract_all_header_paragraphs(docx_path: str):
    """
    Return a list of header paragraphs (strings), collected from all headers,
    looking specifically inside text boxes (w:txbxContent).
    """
    paragraphs = []
    with ZipFile(docx_path) as z:
        for name in z.namelist():
            if name.startswith("word/header") and name.endswith(".xml"):
                xml_bytes = z.read(name)
                root = etree.fromstring(xml_bytes)

                # paragraphs inside text boxes
                for p in root.findall(".//w:txbxContent//w:p", NS):
                    texts = [t.text for t in p.findall(".//w:t", NS) if t.text]
                    para = "".join(texts).strip()
                    if para:
                        paragraphs.append(para)
    return paragraphs

def split_identity_and_sidebar(paragraphs):
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
        return {"title": "", "name": ""}, sections

    # ----- Identity block: everything before first sidebar heading -----
    raw_identity_lines = []
    seen_identity = set()
    for p in paragraphs[:first_section_idx]:
        if p not in seen_identity:
            seen_identity.add(p)
            raw_identity_lines.append(p)

    if raw_identity_lines:
        title = raw_identity_lines[0]
        name = " ".join(raw_identity_lines[1:]) if len(raw_identity_lines) > 1 else ""
    else:
        title = ""
        name = ""

    identity = {"title": title, "name": name}

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
    # Main body via pandoc
    md_text = run_pandoc_to_markdown(docx_path)
    overview, experiences = parse_resume_markdown(md_text)

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

def verify_extracted_data(data: dict, source: Path):
    name = source.stem
    errors = []
    warnings = []

    # --- 1. Critical checks (RED X) ---
    identity = data.get("identity", {})
    if not identity.get("title") or not identity.get("name"):
        errors.append("identity")

    sidebar = data.get("sidebar", {})
    if not any(sidebar.get(section) for section in sidebar):
        errors.append("sidebar")

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
        print(f"❌ {name} ({'; '.join(errors)})")
        return False

    if warnings:
        print(f"⚠️  {name} ({'; '.join(warnings)})")
        return True

    print(f"🟢 {name}")
    return True

def process_single_docx(docx_path: Path, out: Path | None = None):
    """Process one .docx and write its JSON output."""
    data = extract_resume_structure(str(docx_path))
    
    if out is None:
        out = docx_path.with_suffix(".json")

    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    ok = verify_extracted_data(data, docx_path)
    return ok

def apply_template_to_single_file(docx_file: Path, template_path: Path):
    json_path = docx_file.with_suffix(".json")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # OPTIONAL: split name if needed
    name_parts = data["identity"]["name"].split()
    data["identity"]["first_name"] = name_parts[0]
    data["identity"]["last_name"] = " ".join(name_parts[1:])
    data = escape_raw_ampersands_in_obj(data)

    tpl = DocxTemplate(template_path)
    tpl.render(data)

    output_path = docx_file.with_name(docx_file.stem + "_NEW.docx")
    tpl.save(output_path)
    return output_path

def apply_template_to_files(files: list[Path], template_path: Path):
    print("\nApplying template:")

    success = []
    failed = []

    for docx_file in files:
        try:
            output_path = apply_template_to_single_file(docx_file, template_path)
            print(f"🟢 {output_path.name}")
            success.append(docx_file)

        except Exception as e:
            print(f"❌ Failed {docx_file.name}: {e}")
            failed.append(docx_file)

    print(f"\n🟢 {len(success)} generated, ❌ {len(failed)} failed")
    return success, failed


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python resume_extract.py <input.docx> <template.docx>")
        print("  python resume_extract.py <folder> <template.docx>")
        sys.exit(1)

    src = Path(sys.argv[1])
    template_path = Path(sys.argv[2])

    if not template_path.is_file() or template_path.suffix.lower() != ".docx":
        print(f"Template not found or not a .docx: {template_path}")
        sys.exit(1)

    processed = 0
    successful_files = []

    if src.is_file():
        # Single file mode (optional second arg = explicit output path)
        processed = 1
        ok = process_single_docx(src)
        if ok:
            successful_files.append(src.with_suffix(".json"))

    elif src.is_dir():
        # Folder mode: process every .docx in the folder
        for docx_file in src.iterdir():
            if docx_file.is_file() and docx_file.suffix.lower() == ".docx":
                processed += 1
                try:
                    ok = process_single_docx(docx_file)
                    if ok:
                        successful_files.append(docx_file.with_suffix(".json"))
                except Exception as e:
                    print(f"❌ ❌ ❌ Error processing {docx_file}: {e}")
        print("✅ ✅ ✅ Done processing folder.")

    else:
        print(f"Path not found or not a file/folder: {src}")
        sys.exit(1)
    
    # final summary
    success_count = len(successful_files)
    print(f"\n🟢 {success_count} of {processed} files successfully extracted — continue with transformation")

    if success_count > 0:
        apply_template_to_files(successful_files, template_path)

if __name__ == "__main__":
    main()
