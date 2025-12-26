import pytest

import cvextract.sidebar_parser as sp

def test_normalize_sidebar_sections_splits_and_dedupes():
    sections = {
        "skills": ["Python, Python", "AWS  · Azure", "Docker;K8s"],
    }
    out = sp._normalize_sidebar_sections(sections)
    assert out["skills"] == ["Python", "AWS", "Azure", "Docker", "K8s"]

def test_split_identity_and_sidebar_basic():
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

def test_split_identity_and_sidebar_no_sidebar_headings():
    paragraphs = ["Senior Consultant", "Ada Lovelace"]
    identity, sidebar = sp.split_identity_and_sidebar(paragraphs)
    assert identity.full_name == ""
    # sidebar should still have keys (empty lists)
    assert isinstance(sidebar, dict)

def test_split_identity_and_sidebar_without_dots():
    """Test that section titles work both with and without trailing dots."""
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

def test_split_identity_and_sidebar_mixed_dots():
    """Test that section titles can be mixed with and without dots."""
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
