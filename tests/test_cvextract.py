import importlib
import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from cvextract.cli_config import UserConfig
from cvextract.extractors.body_parser import parse_cv_from_docx_body

# Import implementation functions directly
from cvextract.extractors.docx_utils import extract_text_from_w_p
from cvextract.extractors.sidebar_parser import (
    extract_all_header_paragraphs,
    split_identity_and_sidebar,
)
from cvextract.pipeline_helpers import extract_cv_data
from cvextract.shared import UnitOfWork

# -------------------------
# Helpers to build minimal DOCX-like zips
# -------------------------


def _write_docx_zip(
    path: Path, document_xml: str, headers: dict[str, str] | None = None
) -> None:
    """
    Create a minimal .docx-like zip containing:
      - word/document.xml
      - zero or more word/header*.xml parts
    """
    headers = headers or {}
    path.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(path, "w") as z:
        z.writestr("word/document.xml", document_xml)
        for name, xml in headers.items():
            assert name.startswith("word/header") and name.endswith(".xml")
            z.writestr(name, xml)


# -------------------------
# XML fixtures (minimal but valid for our parser)
# -------------------------

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _doc_xml(paragraphs: list[str]) -> str:
    """
    paragraphs: list of already-formed <w:p> ... </w:p> strings
    """
    body = "\n".join(paragraphs)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="{W_NS}">
  <w:body>
    {body}
  </w:body>
</w:document>
""".strip()


def _hdr_xml(paragraphs_inside_txbx: list[str]) -> str:
    """
    paragraphs_inside_txbx: list of already-formed <w:p>...</w:p> strings
    """
    inner = "\n".join(paragraphs_inside_txbx)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:hdr xmlns:w="{W_NS}">
  <w:p>
    <w:r><w:t>ignored</w:t></w:r>
  </w:p>

  <w:txbxContent>
    {inner}
  </w:txbxContent>
</w:hdr>
""".strip()


def _p_text_run(text: str) -> str:
    return f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"


def _p_heading_style(text: str, style_val: str = "Heading1") -> str:
    return f"""
<w:p>
  <w:pPr><w:pStyle w:val="{style_val}"/></w:pPr>
  <w:r><w:t>{text}</w:t></w:r>
</w:p>
""".strip()


def _p_bullet(text: str) -> str:
    # Bullet detected via w:numPr
    return f"""
<w:p>
  <w:pPr><w:numPr/></w:pPr>
  <w:r><w:t>{text}</w:t></w:r>
</w:p>
""".strip()


def _p_with_special_nodes() -> str:
    # Produces "high-quality\tdata\nengineering"
    # using <w:noBreakHyphen/>, <w:tab/>, <w:br/>
    return f"""
<w:p xmlns:w="{W_NS}">
  <w:r><w:t>high</w:t></w:r>
  <w:r><w:noBreakHyphen/></w:r>
  <w:r><w:t>quality</w:t></w:r>
  <w:r><w:tab/></w:r>
  <w:r><w:t>data</w:t></w:r>
  <w:r><w:br/></w:r>
  <w:r><w:t>engineering</w:t></w:r>
</w:p>
""".strip()


def _p_with_soft_hyphen_node() -> str:
    # Produces "high-quality" using <w:softHyphen/>
    return f"""
<w:p xmlns:w="{W_NS}">
  <w:r><w:t>high</w:t></w:r>
  <w:r><w:softHyphen/></w:r>
  <w:r><w:t>quality</w:t></w:r>
</w:p>
""".strip()


# -------------------------
# Unit tests
# -------------------------


def test_normalize_text_replaces_nbsp_and_soft_hyphen_char():
    shared = importlib.import_module("cvextract.shared")
    s = "A\u00a0B high\u00adquality"
    out = shared.normalize_text_for_processing(s)
    assert out == "A B high-quality"


def test_extract_text_from_w_p_handles_hyphen_nodes_breaks_and_tabs():

    du = importlib.import_module("cvextract.extractors.docx_utils")
    from lxml import etree

    xml = _p_with_special_nodes().encode("utf-8")
    p = etree.fromstring(xml)
    out = du.extract_text_from_w_p(p)

    # Should preserve hyphen, tab, and newline
    assert out == "high-quality\tdata\nengineering"


def test_extract_text_from_w_p_handles_soft_hyphen_node():
    from lxml import etree

    xml = _p_with_soft_hyphen_node().encode("utf-8")
    p = etree.fromstring(xml)
    out = extract_text_from_w_p(p)

    assert out == "high-quality"


# -------------------------
# Body parsing tests
# -------------------------


def test_parse_cv_from_docx_body_overview_and_experience(tmp_path: Path):

    doc_xml = _doc_xml(
        [
            _p_text_run("OVERVIEW"),
            _p_text_run("Cloud data engineering leader."),
            _p_text_run("PROFESSIONAL EXPERIENCE"),
            _p_text_run("Jan 2020 – Present — Company X"),
            _p_text_run("Built platforms."),
            _p_bullet("Delivered results."),
        ]
    )

    docx_path = tmp_path / "sample.docx"
    _write_docx_zip(docx_path, doc_xml)

    overview, experiences = parse_cv_from_docx_body(docx_path)
    assert overview == "Cloud data engineering leader."
    assert len(experiences) == 1
    assert experiences[0]["heading"].startswith("Jan 2020")
    assert experiences[0]["description"] == "Built platforms."
    assert experiences[0]["bullets"] == ["Delivered results."]


def test_parse_cv_heading_by_style(tmp_path: Path):

    doc_xml = _doc_xml(
        [
            _p_text_run("PROFESSIONAL EXPERIENCE"),
            _p_heading_style("Role Title — Company Y", style_val="Heading1"),
            _p_text_run("Did stuff."),
            _p_bullet("Shipped."),
        ]
    )

    docx_path = tmp_path / "sample_style.docx"
    _write_docx_zip(docx_path, doc_xml)

    overview, experiences = parse_cv_from_docx_body(docx_path)
    assert overview == ""
    assert len(experiences) == 1
    assert experiences[0]["heading"] == "Role Title — Company Y"
    assert experiences[0]["bullets"] == ["Shipped."]


# -------------------------
# Header/sidebar parsing tests
# -------------------------


def test_header_parsing_splits_identity_and_sidebar_with_linebreaks(tmp_path: Path):

    # Identity lines
    p_title = _p_text_run("Solution Architect")
    p_name = _p_text_run("Rajesh Koothrappali")

    # Sidebar headings/items; put SKILLS. and LANGUAGES. into one <w:p> with <w:br/>
    # so we verify line breaks are preserved and headings don’t get glued.
    p_skills_languages = f"""
<w:p xmlns:w="{W_NS}">
  <w:r><w:t>SKILLS.</w:t></w:r>
  <w:r><w:br/></w:r>
  <w:r><w:t>LANGUAGES.</w:t></w:r>
</w:p>
""".strip()

    p_skills_item = _p_text_run("")
    p_languages_item = _p_text_run("Python • SQL")

    hdr_xml = _hdr_xml(
        [p_title, p_name, p_skills_languages, p_skills_item, p_languages_item]
    )

    doc_xml = _doc_xml([_p_text_run("OVERVIEW"), _p_text_run("X")])
    docx_path = tmp_path / "header_case.docx"
    _write_docx_zip(
        docx_path,
        doc_xml,
        headers={"word/header1.xml": hdr_xml},
    )

    header_paragraphs = extract_all_header_paragraphs(docx_path)
    identity, sidebar = split_identity_and_sidebar(header_paragraphs)

    assert identity.title == "Solution Architect"
    assert identity.full_name == "Rajesh Koothrappali"
    assert identity.first_name == "Rajesh"
    assert identity.last_name == "Koothrappali"

    # Both headings should be recognized as separate lines, not "SKILLS.LANGUAGES."
    assert sidebar["skills"] == []
    assert sidebar["languages"] == ["Python", "SQL"]


# -------------------------
# End-to-end test
# -------------------------


def test_extract_cv_data_end_to_end(tmp_path: Path):

    doc_xml = _doc_xml(
        [
            _p_text_run("OVERVIEW"),
            _p_with_soft_hyphen_node(),  # "high-quality" should survive
            _p_text_run("PROFESSIONAL EXPERIENCE"),
            _p_text_run("Jan 2020 – Present — Company Z"),
            _p_text_run("Built high\u00adquality systems."),  # soft hyphen char -> '-'
            _p_bullet("Improved reliability."),
        ]
    )

    hdr_xml = _hdr_xml(
        [
            _p_text_run("Solution Architect"),
            _p_text_run("Rajesh Koothrappali"),
            _p_text_run("SKILLS."),
            _p_text_run("Python • SQL"),
        ]
    )

    docx_path = tmp_path / "e2e.docx"
    _write_docx_zip(docx_path, doc_xml, headers={"word/header1.xml": hdr_xml})

    output_path = tmp_path / "e2e.json"
    work = UnitOfWork(
        config=UserConfig(target_dir=tmp_path),
        input=docx_path,
        output=output_path,
    )
    extract_cv_data(work)
    data = json.loads(output_path.read_text(encoding="utf-8"))

    assert data["identity"]["full_name"] == "Rajesh Koothrappali"
    assert "high-quality" in data["overview"]  # from the <w:softHyphen/> node paragraph
    assert len(data["experiences"]) == 1
    assert data["experiences"][0]["bullets"] == ["Improved reliability."]
    assert "high-quality" in data["experiences"][0]["description"]
