import cvextract.sidebar_parser as sp


def test_identity_at_end_is_parsed():
    """Identity lines appearing at the end should be parsed correctly."""
    paragraphs = [
        "Languages",
        "C# • PowerShell",
        "Tools",
        "NET • ASP.NET",
        "Industries",
        "Insurance",
        "Spoken languages",
        "German • English",
        "Academic background",
        "Some University",
        # Identity at end
        "Software Engineer",
        "Homer",
        "Simpson",
    ]

    identity, sidebar = sp.split_identity_and_sidebar(paragraphs)

    assert identity.title == "Software Engineer"
    assert identity.full_name == "Homer Simpson"
    assert identity.first_name == "Homer"
    assert identity.last_name == "Simpson"

    # ensure sections captured
    assert sidebar["languages"] == ["C#", "PowerShell"]
    assert sidebar["tools"] == ["NET", "ASP.NET"]
    assert sidebar["industries"] == ["Insurance"]
    assert sidebar["spoken_languages"] == ["German", "English"]
    assert sidebar["academic_background"] == ["Some University"]
