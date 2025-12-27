"""Tests for edge cases in identity parsing."""

import pytest
import cvextract.extractors.sidebar_parser as sp

class TestIdentity:
    """Tests for identity appearing at different positions in paragraphs."""
    
    @pytest.mark.parametrize("paragraphs", [
        [
            # Identity at end
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
            "Software Engineer",
            "Homer",
            "Simpson",
        ],
        [
            # Identity at beginning
            "Software Engineer",
            "Homer",
            "Simpson",
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
        ],
    ])
    def test_parse_with_identity_at_different_positions(self, paragraphs):
        """Test that identity is extracted correctly regardless of position."""
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
