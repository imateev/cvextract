"""Tests for improved coverage of docx_utils and verification modules."""

import pytest
import logging
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from xml.etree import ElementTree as etree
from lxml import etree as lxml_etree

from cvextract.docx_utils import (
    dump_body_sample,
    extract_text_from_w_p,
    _p_style,
    _p_is_bullet,
    iter_document_paragraphs,
    DOCX_NS,
    W_NS,
    XML_PARSER,
)


class TestDumpBodySample:
    """Tests for dump_body_sample debug function."""

    def test_dump_body_sample_exception_handling(self, caplog, tmp_path):
        """Test dump_body_sample handles exceptions gracefully."""
        caplog.set_level(logging.INFO)
        
        bad_docx = tmp_path / "bad.docx"
        bad_docx.write_text("not a zip")
        
        # Should not raise, just log error
        dump_body_sample(bad_docx, n=5)
        
        assert "failed to dump body sample" in caplog.text

    def test_dump_body_sample_success_logs_lines(self, caplog, tmp_path):
        """Test dump_body_sample logs paragraphs successfully."""
        from zipfile import ZipFile
        
        caplog.set_level(logging.INFO)
        
        # Create a minimal valid DOCX
        docx_path = tmp_path / "test.docx"
        with ZipFile(docx_path, "w") as z:
            xml_content = b"""<?xml version="1.0"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p>
            <w:pPr>
                <w:pStyle w:val="Normal"/>
                <w:numPr><w:ilvl w:val="0"/></w:numPr>
            </w:pPr>
            <w:r><w:t>Bullet point</w:t></w:r>
        </w:p>
        <w:p>
            <w:r><w:t>Normal text</w:t></w:r>
        </w:p>
    </w:body>
</w:document>"""
            z.writestr("word/document.xml", xml_content)
        
        dump_body_sample(docx_path, n=10)
        
        assert "BODY SAMPLE" in caplog.text


class TestExtractTextFromWp:
    """Tests for text extraction from Word paragraph elements."""

    def test_extract_text_basic(self):
        """Test extracting simple text from paragraph."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:r><w:t>Hello</w:t></w:r></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        text = extract_text_from_w_p(p)
        assert text == "Hello"

    def test_extract_text_no_break_hyphen(self):
        """Test noBreakHyphen is converted to dash."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:r><w:noBreakHyphen/></w:r></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        text = extract_text_from_w_p(p)
        assert "-" in text

    def test_extract_text_soft_hyphen(self):
        """Test softHyphen is converted to dash."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:r><w:softHyphen/></w:r></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        text = extract_text_from_w_p(p)
        assert "-" in text

    def test_extract_text_line_break(self):
        """Test br element is converted to newline."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:r><w:t>Line1</w:t><w:br/><w:t>Line2</w:t></w:r></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        text = extract_text_from_w_p(p)
        assert "\n" in text and "Line1" in text and "Line2" in text

    def test_extract_text_carriage_return(self):
        """Test cr element is converted to newline."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:r><w:t>Before</w:t><w:cr/><w:t>After</w:t></w:r></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        text = extract_text_from_w_p(p)
        assert "\n" in text and "Before" in text and "After" in text

    def test_extract_text_tab(self):
        """Test tab element is converted to tab character."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:r><w:t>A</w:t><w:tab/><w:t>B</w:t></w:r></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        text = extract_text_from_w_p(p)
        assert "\t" in text

    def test_extract_text_empty_t_element(self):
        """Test that empty t elements are skipped."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:r><w:t></w:t><w:t>Text</w:t></w:r></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        text = extract_text_from_w_p(p)
        assert text == "Text"

    def test_extract_text_multiple_runs(self):
        """Test extracting text from multiple runs."""
        xml = f'''<w:p xmlns:w="{W_NS}">
            <w:r><w:t>Hello</w:t></w:r>
            <w:r><w:t> </w:t></w:r>
            <w:r><w:t>World</w:t></w:r>
        </w:p>'''
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        text = extract_text_from_w_p(p)
        assert "Hello" in text and "World" in text


class TestPStyle:
    """Tests for _p_style function."""

    def test_p_style_none(self):
        """Test _p_style returns empty string when no style."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:pPr></w:pPr></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        style = _p_style(p)
        assert style == ""

    def test_p_style_with_value(self):
        """Test _p_style returns style value."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:pPr><w:pStyle w:val="Heading1"/></w:pPr></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        style = _p_style(p)
        assert style == "Heading1"

    def test_p_style_empty_val(self):
        """Test _p_style handles empty val attribute."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:pPr><w:pStyle w:val=""/></w:pPr></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        style = _p_style(p)
        assert style == ""


class TestPIsBullet:
    """Tests for _p_is_bullet function."""

    def test_p_is_bullet_with_numPr(self):
        """Test _p_is_bullet detects numPr element."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:pPr><w:numPr><w:ilvl w:val="0"/></w:numPr></w:pPr></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        assert _p_is_bullet(p) is True

    def test_p_is_bullet_list_style(self):
        """Test _p_is_bullet detects 'list' in style name."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:pPr><w:pStyle w:val="ListStyle"/></w:pPr></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        assert _p_is_bullet(p) is True

    def test_p_is_bullet_bullet_style(self):
        """Test _p_is_bullet detects 'bullet' in style name."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:pPr><w:pStyle w:val="BulletPoint"/></w:pPr></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        assert _p_is_bullet(p) is True

    def test_p_is_bullet_number_style(self):
        """Test _p_is_bullet detects 'number' in style name."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:pPr><w:pStyle w:val="NumberedList"/></w:pPr></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        assert _p_is_bullet(p) is True

    def test_p_is_bullet_case_insensitive(self):
        """Test _p_is_bullet is case-insensitive for style matching."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:pPr><w:pStyle w:val="LISTPARAGRAPH"/></w:pPr></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        assert _p_is_bullet(p) is True

    def test_p_is_bullet_not_bullet(self):
        """Test _p_is_bullet returns False for normal paragraph."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:pPr><w:pStyle w:val="Normal"/></w:pPr></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        assert _p_is_bullet(p) is False

    def test_p_is_bullet_no_pPr(self):
        """Test _p_is_bullet returns False when no pPr element."""
        xml = f'<w:p xmlns:w="{W_NS}"><w:r><w:t>Text</w:t></w:r></w:p>'
        p = lxml_etree.fromstring(xml.encode(), XML_PARSER)
        
        assert _p_is_bullet(p) is False
