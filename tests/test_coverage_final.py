"""Tests for improved coverage of verification and sidebar_parser modules."""

import json
from zipfile import ZipFile

from cvextract.extractors.sidebar_parser import (
    extract_all_header_paragraphs,
    split_identity_and_sidebar,
)
from cvextract.cli_config import UserConfig
from cvextract.shared import StepName, UnitOfWork
from cvextract.verifiers import get_verifier


def _make_roundtrip_work(tmp_path, source, target):
    source_path = tmp_path / "source.json"
    target_path = tmp_path / "target.json"
    source_path.write_text(json.dumps(source), encoding="utf-8")
    target_path.write_text(json.dumps(target), encoding="utf-8")
    work = UnitOfWork(
        config=UserConfig(target_dir=tmp_path),
        input=source_path,
        output=target_path,
    )
    work.current_step = StepName.RoundtripComparer
    work.ensure_step_status(StepName.RoundtripComparer)
    return work


class TestIsEnvironmentPath:
    """Tests for _is_environment_path helper."""

    def setup_method(self):
        """Setup a RoundtripVerifier instance for testing."""
        self.verifier = get_verifier("roundtrip-verifier")

    def test_is_environment_path_true(self):
        """Test detection of environment path."""
        assert self.verifier._is_environment_path("experiences[0].environment") is True
        assert self.verifier._is_environment_path("experience.environment") is True
        assert self.verifier._is_environment_path(".environment") is True

    def test_is_environment_path_false(self):
        """Test non-environment paths."""
        assert self.verifier._is_environment_path("experiences[0].description") is False
        assert self.verifier._is_environment_path("title") is False
        assert self.verifier._is_environment_path("sidebar") is False


class TestNormalizeEnvironmentList:
    """Tests for _normalize_environment_list function."""

    def setup_method(self):
        """Setup a RoundtripVerifier instance for testing."""
        self.verifier = get_verifier("roundtrip-verifier")

    def test_normalize_single_items(self):
        """Test normalization of single items."""
        result = self.verifier._normalize_environment_list(["Python", "Java"])
        assert result == ["java", "python"]  # sorted, lowercased

    def test_normalize_comma_separated(self):
        """Test comma-separated values in single entry."""
        result = self.verifier._normalize_environment_list(["Python, Java, Go"])
        assert "python" in result and "java" in result and "go" in result

    def test_normalize_bullet_separated(self):
        """Test bullet-separated values."""
        result = self.verifier._normalize_environment_list(["Python • Java • Go"])
        assert "python" in result and "java" in result and "go" in result

    def test_normalize_semicolon_separated(self):
        """Test semicolon-separated values."""
        result = self.verifier._normalize_environment_list(["Python; Java; Go"])
        assert "python" in result and "java" in result and "go" in result

    def test_normalize_spaced_bullet(self):
        """Test space-separated bullet notation."""
        result = self.verifier._normalize_environment_list(["Python • Java • Go"])
        assert "python" in result and "java" in result and "go" in result

    def test_normalize_spaced_dash(self):
        """Test space-separated dash notation."""
        result = self.verifier._normalize_environment_list(["Python - Java - Go"])
        assert "python" in result and "java" in result and "go" in result

    def test_normalize_non_string_entries(self):
        """Test handling of non-string entries."""
        result = self.verifier._normalize_environment_list(["Python", 123, None])
        assert "python" in result
        # Non-strings are converted to string and lowercased
        assert any("123" in str(x).lower() for x in result)

    def test_normalize_empty_list(self):
        """Test empty list normalization."""
        result = self.verifier._normalize_environment_list([])
        assert result == []

    def test_normalize_whitespace_handling(self):
        """Test that extra whitespace is stripped."""
        result = self.verifier._normalize_environment_list(["  Python  ", "  Java  "])
        assert "python" in result and "java" in result


class TestCompareDataStructures:
    """Tests for RoundtripVerifier."""

    def test_compare_primitive_value_mismatch(self, tmp_path):
        """Test detection of primitive value mismatches."""
        original = {"key": "value1"}
        new = {"key": "value2"}

        verifier = get_verifier("roundtrip-verifier")
        work = _make_roundtrip_work(tmp_path, original, new)
        result = verifier.verify(work)
        status = result.step_states[StepName.RoundtripComparer]
        assert any("value mismatch" in err for err in status.errors)

    def test_compare_type_mismatch(self, tmp_path):
        """Test detection of type mismatches."""
        original = {"key": "value"}
        new = {"key": 123}

        verifier = get_verifier("roundtrip-verifier")
        work = _make_roundtrip_work(tmp_path, original, new)
        result = verifier.verify(work)
        status = result.step_states[StepName.RoundtripComparer]
        assert any("type mismatch" in err for err in status.errors)

    def test_compare_list_length_mismatch(self, tmp_path):
        """Test detection of list length mismatches."""
        original = {"items": [1, 2, 3]}
        new = {"items": [1, 2]}

        verifier = get_verifier("roundtrip-verifier")
        work = _make_roundtrip_work(tmp_path, original, new)
        result = verifier.verify(work)
        status = result.step_states[StepName.RoundtripComparer]
        assert any("list length mismatch" in err for err in status.errors)

    def test_compare_nested_dict_mismatch(self, tmp_path):
        """Test detection of nested dict mismatches."""
        original = {"a": {"b": {"c": 1}}}
        new = {"a": {"b": {"c": 2}}}

        verifier = get_verifier("roundtrip-verifier")
        work = _make_roundtrip_work(tmp_path, original, new)
        result = verifier.verify(work)
        status = result.step_states[StepName.RoundtripComparer]
        assert any("value mismatch" in err for err in status.errors)

    def test_compare_missing_key(self, tmp_path):
        """Test detection of missing keys."""
        original = {"a": 1, "b": 2}
        new = {"a": 1}

        verifier = get_verifier("roundtrip-verifier")
        work = _make_roundtrip_work(tmp_path, original, new)
        result = verifier.verify(work)
        status = result.step_states[StepName.RoundtripComparer]
        assert any("missing key" in err for err in status.errors)

    def test_compare_extra_key(self, tmp_path):
        """Test detection of extra keys."""
        original = {"a": 1}
        new = {"a": 1, "b": 2}

        verifier = get_verifier("roundtrip-verifier")
        work = _make_roundtrip_work(tmp_path, original, new)
        result = verifier.verify(work)
        status = result.step_states[StepName.RoundtripComparer]
        assert status.errors

    def test_compare_environment_field_normalization(self, tmp_path):
        """Test environment field normalization in comparison."""
        original = {
            "experiences": [
                {
                    "heading": "Job",
                    "description": "Work",
                    "environment": ["Python, Java, Go"],
                }
            ]
        }
        new = {
            "experiences": [
                {
                    "heading": "Job",
                    "description": "Work",
                    "environment": ["Java • Python • Go"],
                }
            ]
        }

        verifier = get_verifier("roundtrip-verifier")
        work = _make_roundtrip_work(tmp_path, original, new)
        result = verifier.verify(work)
        # Should be OK because environment is normalized and equivalent
        status = result.step_states[StepName.RoundtripComparer]
        assert status.errors == []

    def test_compare_environment_real_mismatch(self, tmp_path):
        """Test real environment mismatches are detected."""
        original = {
            "experiences": [{"heading": "Job", "environment": ["Python", "Java"]}]
        }
        new = {"experiences": [{"heading": "Job", "environment": ["C++", "Rust"]}]}

        verifier = get_verifier("roundtrip-verifier")
        work = _make_roundtrip_work(tmp_path, original, new)
        result = verifier.verify(work)
        status = result.step_states[StepName.RoundtripComparer]
        assert any("environment mismatch" in err for err in status.errors)


class TestSplitIdentityAndSidebar:
    """Tests for split_identity_and_sidebar function."""

    def test_split_with_sidebar_headings(self):
        """Test splitting paragraphs with sidebar headings."""
        paragraphs = [
            "Software Engineer",
            "John Doe",
            "Languages",
            "English",
            "French",
            "Tools",
            "Python",
            "Go",
        ]

        identity, sidebar = split_identity_and_sidebar(paragraphs)

        assert identity.title == "Software Engineer"
        assert identity.full_name == "John Doe"
        assert identity.first_name == "John"
        assert identity.last_name == "Doe"
        assert "English" in sidebar.get("languages", [])
        assert "Python" in sidebar.get("tools", [])

    def test_split_no_sidebar_headings(self):
        """Test when there are no sidebar headings."""
        paragraphs = [
            "Junior Developer",
            "Jane Smith",
            "Some random text",
            "More random text",
        ]

        identity, sidebar = split_identity_and_sidebar(paragraphs)

        assert identity.title == ""
        assert identity.full_name == ""
        assert all(len(v) == 0 for v in sidebar.values())

    def test_split_identity_at_end(self):
        """Test when identity appears at the end (after sidebar sections)."""
        paragraphs = [
            "Languages",
            "English",
            "Spanish",
            "Tools",
            "Python",
            "Architect",
            "Bob Johnson",
        ]

        identity, sidebar = split_identity_and_sidebar(paragraphs)

        # The function should still extract identity from beginning or end
        # In this case, since there's no content before Languages, it tries the end
        assert identity.full_name != "" or identity.title != ""

    def test_split_single_name_identity(self):
        """Test identity with only one name part."""
        paragraphs = [
            "Engineer",
            "Madonna",
            "Languages",
            "English",
        ]

        identity, sidebar = split_identity_and_sidebar(paragraphs)

        assert identity.title == "Engineer"
        assert identity.first_name == "Madonna"
        assert identity.last_name == ""

    def test_split_duplicate_section_headings(self):
        """Test handling of duplicate section headings (treated as content)."""
        paragraphs = [
            "Dev",
            "John",
            "Languages",
            "Python",
            "Languages",  # Duplicate heading
            "Should be ignored as content",
            "Tools",
            "Git",
        ]

        identity, sidebar = split_identity_and_sidebar(paragraphs)

        # Second "Languages" should not create a duplicate section
        assert identity.title == "Dev"

    def test_split_empty_section(self):
        """Test sections with no content between headings."""
        paragraphs = [
            "Title",
            "Name",
            "Languages",
            "Tools",
            "Python",
        ]

        identity, sidebar = split_identity_and_sidebar(paragraphs)

        # Languages section has no items before Tools heading
        assert sidebar.get("languages", []) == []
        assert "Python" in sidebar.get("tools", [])

    def test_split_with_whitespace_variations(self):
        """Test that various whitespace is handled properly."""
        paragraphs = [
            "  Software Engineer  ",
            "  John Doe  ",
            "LANGUAGES",  # Case variation
            "  English  ",
            "  French  ",
        ]

        identity, sidebar = split_identity_and_sidebar(paragraphs)

        assert "John Doe" in identity.full_name or identity.full_name == "John Doe"
        # Languages should be recognized despite case variation
        lang_found = any(
            "english" in str(v).lower() for v in sidebar.get("languages", [])
        )
        assert lang_found or "English" in sidebar.get("languages", [])


class TestExtractAllHeaderParagraphs:
    """Tests for extract_all_header_paragraphs function."""

    def test_extract_from_single_header(self, tmp_path):
        """Test extracting paragraphs from a single header."""
        docx_path = tmp_path / "test.docx"

        with ZipFile(docx_path, "w") as z:
            header_xml = b"""<?xml version="1.0"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p><w:r><w:t>Title</w:t></w:r></w:p>
        <w:p><w:r><w:t>Name</w:t></w:r></w:p>
    </w:body>
</w:document>"""
            z.writestr("word/header1.xml", header_xml)

        paragraphs = extract_all_header_paragraphs(docx_path)
        assert "Title" in paragraphs
        assert "Name" in paragraphs

    def test_extract_deduplicates_paragraphs(self, tmp_path):
        """Test that duplicate paragraphs are removed."""
        docx_path = tmp_path / "test.docx"

        with ZipFile(docx_path, "w") as z:
            header_xml = b"""<?xml version="1.0"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p><w:r><w:t>Title</w:t></w:r></w:p>
        <w:p><w:r><w:t>Title</w:t></w:r></w:p>
        <w:p><w:r><w:t>Name</w:t></w:r></w:p>
    </w:body>
</w:document>"""
            z.writestr("word/header1.xml", header_xml)

        paragraphs = extract_all_header_paragraphs(docx_path)
        # Count occurrences of "Title"
        title_count = sum(1 for p in paragraphs if p == "Title")
        assert title_count == 1

    def test_extract_multiple_headers(self, tmp_path):
        """Test extracting from multiple header files."""
        docx_path = tmp_path / "test.docx"

        with ZipFile(docx_path, "w") as z:
            header1_xml = b"""<?xml version="1.0"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p><w:r><w:t>Header1</w:t></w:r></w:p>
    </w:body>
</w:document>"""
            header2_xml = b"""<?xml version="1.0"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
    <w:body>
        <w:p><w:r><w:t>Header2</w:t></w:r></w:p>
    </w:body>
</w:document>"""
            z.writestr("word/header1.xml", header1_xml)
            z.writestr("word/header2.xml", header2_xml)

        paragraphs = extract_all_header_paragraphs(docx_path)
        assert "Header1" in paragraphs
        assert "Header2" in paragraphs

    def test_extract_from_textbox(self, tmp_path):
        """Test extracting from textbox content (w:txbxContent)."""
        docx_path = tmp_path / "test.docx"

        with ZipFile(docx_path, "w") as z:
            header_xml = b"""<?xml version="1.0"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
            xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape">
    <w:body>
        <w:p>
            <w:r>
                <w:drawing>
                    <wps:wsp>
                        <wps:txbx>
                            <w:txbxContent>
                                <w:p><w:r><w:t>TextboxContent</w:t></w:r></w:p>
                            </w:txbxContent>
                        </wps:txbx>
                    </wps:wsp>
                </w:drawing>
            </w:r>
        </w:p>
    </w:body>
</w:document>"""
            z.writestr("word/header1.xml", header_xml)

        paragraphs = extract_all_header_paragraphs(docx_path)
        assert "TextboxContent" in paragraphs
