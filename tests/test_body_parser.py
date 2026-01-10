"""Tests for body parser functionality."""

from pathlib import Path

import cvextract.extractors.body_parser as bp


class TestCVBodyParsing:
    """Tests for parsing CV body content from DOCX."""

    def test_parse_complete_cv_structure_extracts_all_sections(self, monkeypatch):
        """When CV has overview, experience with bullets and environment, should parse all correctly."""
        stream = [
            ("OVERVIEW", False, ""),
            ("Some overview text", False, ""),
            ("PROFESSIONAL EXPERIENCE", False, ""),
            ("Jan 2020 - Present | Company", False, "Heading1"),
            ("Did things", False, ""),
            ("• bullet 1", True, ""),
            ("Environment: Python, AWS", False, ""),
        ]

        def fake_iter(_path: Path):
            for t in stream:
                yield t

        monkeypatch.setattr(bp, "iter_document_paragraphs", fake_iter)

        overview, exps = bp.parse_cv_from_docx_body(Path("fake.docx"))
        assert overview == "Some overview text"
        assert len(exps) == 1
        assert exps[0]["heading"].startswith("Jan 2020")
        assert "Did things" in exps[0]["description"]
        assert exps[0]["bullets"] == ["• bullet 1"] or exps[0]["bullets"] == [
            "bullet 1"
        ]
        assert exps[0]["environment"] == ["Python", "AWS"]

    def test_parse_with_text_outside_sections_ignores_it(self, monkeypatch):
        """When text appears before any section markers, should be ignored."""
        stream = [
            ("Random header-like junk", False, ""),
            ("Another line", False, ""),
        ]

        def fake_iter(_path: Path):
            yield from stream

        monkeypatch.setattr(bp, "iter_document_paragraphs", fake_iter)

        overview, exps = bp.parse_cv_from_docx_body(Path("fake.docx"))
        assert overview == ""
        assert exps == []

    def test_parse_with_empty_lines_skips_them(self, monkeypatch):
        """Empty lines and whitespace-only lines should be skipped."""
        stream = [
            ("OVERVIEW", False, ""),
            ("", False, ""),  # Empty line
            ("  ", False, ""),  # Whitespace-only
            ("Some overview text", False, ""),
            ("PROFESSIONAL EXPERIENCE", False, ""),
            ("", False, ""),  # Empty line in experience section
            ("Jan 2020 - Present | Company", False, "Heading1"),
        ]

        def fake_iter(_path: Path):
            for t in stream:
                yield t

        monkeypatch.setattr(bp, "iter_document_paragraphs", fake_iter)

        overview, exps = bp.parse_cv_from_docx_body(Path("fake.docx"))
        assert overview == "Some overview text"
        assert len(exps) == 1

    def test_parse_year_only_headings(self, monkeypatch):
        """Year-only headings should be treated as experience headings."""
        stream = [
            ("PROFESSIONAL EXPERIENCE", False, ""),
            ("2021 | Student Consultant Data Strategy", False, ""),
            ("Did work", False, ""),
            ("2022 – 2024 | Inhouse Consultant Business Intelligence", False, ""),
            ("More work", False, ""),
        ]

        def fake_iter(_path: Path):
            for t in stream:
                yield t

        monkeypatch.setattr(bp, "iter_document_paragraphs", fake_iter)

        overview, exps = bp.parse_cv_from_docx_body(Path("fake.docx"))
        assert overview == ""
        assert len(exps) == 2
        assert exps[0]["heading"].startswith("2021 |")
        assert exps[1]["heading"].startswith("2022 – 2024")
