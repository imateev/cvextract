import pytest

from pathlib import Path
import cvextract.body_parser as bp

def test_parse_cv_from_docx_body_happy_path(monkeypatch):
    # (text, is_bullet, style)
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
    assert exps[0]["bullets"] == ["• bullet 1"] or exps[0]["bullets"] == ["bullet 1"]
    assert exps[0]["environment"] == ["Python", "AWS"]


def test_parse_cv_from_docx_body_ignores_text_outside_sections(monkeypatch):
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
