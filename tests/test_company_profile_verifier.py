"""
Tests for CompanyProfileVerifier.
"""

import pytest
from cvextract.verifiers.company_profile_verifier import CompanyProfileVerifier
from cvextract.verifiers import get_verifier


class TestCompanyProfileVerifier:
    """Tests for CompanyProfileVerifier."""

    @pytest.fixture
    def verifier(self):
        """Create a CompanyProfileVerifier instance."""
        return CompanyProfileVerifier()

    def test_valid_minimal_profile(self, verifier):
        """Test that minimal valid company profile passes."""
        data = {
            "name": "Acme Corp",
            "domains": ["technology"],
        }
        result = verifier.verify(data)
        assert result.ok
        assert not result.errors

    def test_valid_full_profile(self, verifier):
        """Test that full company profile passes."""
        data = {
            "name": "Acme Corporation",
            "description": "A leading technology company",
            "domains": ["technology", "consulting"],
            "technology_signals": [
                {
                    "technology": "Python",
                    "category": "programming",
                    "interest_level": "high",
                    "confidence": 0.95,
                    "signals": ["GitHub repos"],
                    "notes": "Heavy use in data pipelines",
                }
            ],
            "industry_classification": {
                "naics": "541511",
                "sic": "7372",
            },
            "founded_year": 2010,
            "headquarters": {
                "city": "San Francisco",
                "state": "CA",
                "country": "USA",
            },
            "company_size": "large",
            "employee_count": 5000,
            "ownership_type": "public",
            "website": "https://acme.com",
        }
        result = verifier.verify(data)
        assert result.ok
        assert not result.errors

    def test_missing_required_name(self, verifier):
        """Test that missing name fails."""
        data = {"domains": ["technology"]}
        result = verifier.verify(data)
        assert not result.ok
        assert any("name" in err for err in result.errors)

    def test_missing_required_domains(self, verifier):
        """Test that missing domains fails."""
        data = {"name": "Acme Corp"}
        result = verifier.verify(data)
        assert not result.ok
        assert any("domains" in err for err in result.errors)

    def test_name_empty_string_fails(self, verifier):
        """Test that empty name fails."""
        data = {"name": "", "domains": ["technology"]}
        result = verifier.verify(data)
        assert not result.ok
        assert any("name must be a non-empty string" in err for err in result.errors)

    def test_name_not_string_fails(self, verifier):
        """Test that non-string name fails."""
        data = {"name": 123, "domains": ["technology"]}
        result = verifier.verify(data)
        assert not result.ok
        assert any("name must be a string" in err for err in result.errors)

    def test_domains_empty_array_fails(self, verifier):
        """Test that empty domains array fails."""
        data = {"name": "Acme", "domains": []}
        result = verifier.verify(data)
        assert not result.ok
        assert any("at least one item" in err for err in result.errors)

    def test_domains_not_array_fails(self, verifier):
        """Test that non-array domains fails."""
        data = {"name": "Acme", "domains": "technology"}
        result = verifier.verify(data)
        assert not result.ok
        assert any("domains must be an array" in err for err in result.errors)

    def test_domains_non_string_items_fail(self, verifier):
        """Test that non-string domain items fail."""
        data = {"name": "Acme", "domains": ["technology", 123]}
        result = verifier.verify(data)
        assert not result.ok
        assert any("domains items must be strings" in err for err in result.errors)

    def test_description_not_string_fails(self, verifier):
        """Test that non-string description fails."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "description": 123,
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("description must be a string" in err for err in result.errors)

    def test_technology_signals_missing_required_field(self, verifier):
        """Test that signal missing technology field fails."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "technology_signals": [{"category": "programming"}],
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("missing required field: technology" in err for err in result.errors)

    def test_technology_signals_invalid_interest_level(self, verifier):
        """Test that invalid interest_level fails."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "technology_signals": [
                {
                    "technology": "Python",
                    "interest_level": "invalid",
                }
            ],
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("interest_level must be" in err for err in result.errors)

    def test_technology_signals_invalid_confidence(self, verifier):
        """Test that invalid confidence fails."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "technology_signals": [
                {
                    "technology": "Python",
                    "confidence": 1.5,  # Out of range
                }
            ],
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("confidence must be" in err for err in result.errors)

    def test_founded_year_out_of_range(self, verifier):
        """Test that out-of-range founded_year fails."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "founded_year": 1500,
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("founded_year must be" in err for err in result.errors)

    def test_headquarters_missing_country(self, verifier):
        """Test that headquarters without country fails."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "headquarters": {"city": "San Francisco"},
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("country" in err for err in result.errors)

    def test_company_size_invalid_value(self, verifier):
        """Test that invalid company_size fails."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "company_size": "huge",
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("company_size must be" in err for err in result.errors)

    def test_employee_count_invalid_value(self, verifier):
        """Test that invalid employee_count fails."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "employee_count": 0,
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("employee_count must be" in err for err in result.errors)

    def test_ownership_type_invalid_value(self, verifier):
        """Test that invalid ownership_type fails."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "ownership_type": "cooperative",
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("ownership_type must be" in err for err in result.errors)

    def test_registry_access(self):
        """Test that CompanyProfileVerifier is accessible via registry."""
        verifier = get_verifier("company-profile-verifier")
        assert verifier is not None
        assert isinstance(verifier, CompanyProfileVerifier)

    def test_verify_with_none_optional_fields(self, verifier):
        """Test that None values for optional fields pass."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "description": None,
            "founded_year": None,
            "headquarters": None,
            "company_size": None,
            "employee_count": None,
            "ownership_type": None,
            "website": None,
        }
        result = verifier.verify(data)
        assert result.ok
        assert not result.errors

    def test_verify_with_partial_headquarters(self, verifier):
        """Test that partial headquarters object is valid."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "headquarters": {
                "country": "USA",
                "city": "San Francisco",
            },
        }
        result = verifier.verify(data)
        assert result.ok
        assert not result.errors

    def test_verify_technology_signals_with_null_optional_fields(self, verifier):
        """Test technology signals with null optional fields."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "technology_signals": [
                {
                    "technology": "Python",
                    "category": None,
                    "interest_level": None,
                    "notes": None,
                }
            ],
        }
        result = verifier.verify(data)
        assert result.ok
        assert not result.errors
