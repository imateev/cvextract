"""Tests for sidebar/header parsing functionality."""

import pytest
import cvextract.extractors.sidebar_parser as sp


class TestSidebarNormalization:
    """Tests for normalizing sidebar section data."""

    def test_normalize_with_multiple_separators_splits_and_deduplicates(self):
        """Skills with commas, bullets, semicolons should be split and duplicates removed."""
        sections = {
            "skills": ["Python, Python", "AWS  · Azure", "Docker;K8s"],
        }
        out = sp._normalize_sidebar_sections(sections)
        assert out["skills"] == ["Python", "AWS", "Azure", "Docker", "K8s"]

    def test_normalize_with_empty_strings_filters_them_out(self):
        """Empty strings after splitting should be filtered out."""
        sections = {
            "skills": ["Python,  ,  AWS", "  "],
        }
        out = sp._normalize_sidebar_sections(sections)
        assert out["skills"] == ["Python", "AWS"]

    def test_normalize_with_empty_parts_after_split_skips_them(self):
        """When splitting produces empty parts, they should be skipped."""
        sections = {
            "languages": ["English,,,French", ";;German"],
        }
        out = sp._normalize_sidebar_sections(sections)
        assert out["languages"] == ["English", "French", "German"]


class TestIdentityAndSidebarParsing:
    """Tests for parsing identity and sidebar from paragraphs."""

    def test_parse_with_standard_format_extracts_identity_and_sections(self):
        """Standard format with title, name, and sections should be parsed correctly."""
        paragraphs = [
            "Senior Consultant",
            "Ada Lovelace",
            "SKILLS.",
            "Python, AWS",
            "LANGUAGES.",
            "English",
        ]
        identity, sidebar = sp.split_identity_and_sidebar(paragraphs)

        assert identity.title == "Senior Consultant"
        assert identity.full_name == "Ada Lovelace"
        assert identity.first_name == "Ada"
        assert identity.last_name == "Lovelace"

        assert sidebar["skills"] == ["Python", "AWS"]
        assert sidebar["languages"] == ["English"]

    def test_parse_with_no_sidebar_headings_returns_empty_identity(self):
        """When no sidebar section headings exist, should return empty identity."""
        paragraphs = ["Senior Consultant", "Ada Lovelace"]
        identity, sidebar = sp.split_identity_and_sidebar(paragraphs)
        assert identity.full_name == ""
        assert isinstance(sidebar, dict)

    def test_parse_with_headings_without_dots_recognizes_sections(self):
        """Section titles without trailing dots should still be recognized."""
        paragraphs = [
            "Senior Consultant",
            "Ada Lovelace",
            "SKILLS",  # Without dot
            "Python, AWS",
            "LANGUAGES",  # Without dot
            "English",
        ]
        identity, sidebar = sp.split_identity_and_sidebar(paragraphs)

        assert identity.title == "Senior Consultant"
        assert identity.full_name == "Ada Lovelace"
        assert sidebar["skills"] == ["Python", "AWS"]
        assert sidebar["languages"] == ["English"]

    def test_parse_with_mixed_dot_formats_handles_both(self):
        """Section titles can be mixed with and without dots in same document."""
        paragraphs = [
            "Senior Consultant",
            "Ada Lovelace",
            "SKILLS.",  # With dot
            "Python, AWS",
            "LANGUAGES",  # Without dot
            "English",
            "TOOLS.",  # With dot
            "Docker, K8s",
        ]
        identity, sidebar = sp.split_identity_and_sidebar(paragraphs)

        assert sidebar["skills"] == ["Python", "AWS"]
        assert sidebar["languages"] == ["English"]
        assert sidebar["tools"] == ["Docker", "K8s"]

    def test_parse_with_trailing_colons_recognizes_headings(self):
        """Headings with trailing colons should be recognized as section markers."""
        paragraphs = [
            "Senior Consultant",
            "Ada Lovelace",
            "SKILLS:",
            "Python; AWS",
            "LANGUAGES:",
            "English; French",
        ]

        identity, sidebar = sp.split_identity_and_sidebar(paragraphs)

        assert identity.full_name == "Ada Lovelace"
        assert sidebar["skills"] == ["Python", "AWS"]
        assert sidebar["languages"] == ["English", "French"]
