"""
Low-level DOCX / WordprocessingML helpers.

This module handles direct extraction of text and metadata from DOCX files:
- reading Word XML parts
- iterating document paragraphs
- detecting bullets and paragraph styles
- converting Word runs into plain text

It contains no CV-specific logic; higher-level parsing is handled elsewhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, List, Tuple
from zipfile import ZipFile

from lxml import etree

from ..logging_utils import LOG
from ..shared import (
    normalize_text_for_processing,
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
