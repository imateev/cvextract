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
    def test_technology_signals_not_array(self, verifier):
        """Test that technology_signals must be an array."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "technology_signals": "not an array",
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("array" in err for err in result.errors)

    def test_technology_signals_item_not_dict(self, verifier):
        """Test that technology_signals items must be objects."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "technology_signals": ["not a dict"],
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("must be an object" in err for err in result.errors)

    def test_technology_signals_technology_not_string(self, verifier):
        """Test that technology field must be a string."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "technology_signals": [
                {
                    "technology": 123,
                }
            ],
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("technology must be a string" in err for err in result.errors)

    def test_technology_signals_category_not_string(self, verifier):
        """Test that category must be a string or null."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "technology_signals": [
                {
                    "technology": "Python",
                    "category": 123,
                }
            ],
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("category must be a string" in err for err in result.errors)

    def test_technology_signals_signals_not_array(self, verifier):
        """Test that signals field must be an array."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "technology_signals": [
                {
                    "technology": "Python",
                    "signals": "not an array",
                }
            ],
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("signals must be an array" in err for err in result.errors)

    def test_technology_signals_signals_items_not_strings(self, verifier):
        """Test that signals items must be strings."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "technology_signals": [
                {
                    "technology": "Python",
                    "signals": ["valid", 123],
                }
            ],
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("signals items must be strings" in err for err in result.errors)

    def test_technology_signals_notes_not_string(self, verifier):
        """Test that notes must be a string or null."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "technology_signals": [
                {
                    "technology": "Python",
                    "notes": 123,
                }
            ],
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("notes must be a string" in err for err in result.errors)

    def test_industry_classification_not_object(self, verifier):
        """Test that industry_classification must be an object or null."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "industry_classification": "not an object",
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("industry_classification must be an object" in err for err in result.errors)

    def test_industry_classification_naics_not_string(self, verifier):
        """Test that naics must be a string or null."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "industry_classification": {
                "naics": 123,
            },
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("naics must be a string" in err for err in result.errors)

    def test_industry_classification_sic_not_string(self, verifier):
        """Test that sic must be a string or null."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "industry_classification": {
                "sic": 123,
            },
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("sic must be a string" in err for err in result.errors)

    def test_headquarters_not_object(self, verifier):
        """Test that headquarters must be an object or null."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "headquarters": "not an object",
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("headquarters must be an object" in err for err in result.errors)

    def test_headquarters_city_not_string(self, verifier):
        """Test that city must be a string or null."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "headquarters": {
                "country": "USA",
                "city": 123,
            },
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("city must be a string" in err for err in result.errors)

    def test_headquarters_state_not_string(self, verifier):
        """Test that state must be a string or null."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "headquarters": {
                "country": "USA",
                "state": 123,
            },
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("state must be a string" in err for err in result.errors)

    def test_headquarters_country_not_string(self, verifier):
        """Test that country must be a string or null."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "headquarters": {
                "country": 123,
            },
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("country must be a string" in err for err in result.errors)

    def test_website_not_string(self, verifier):
        """Test that website must be a string or null."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "website": 123,
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("website must be a string" in err for err in result.errors)

    def test_employee_count_not_integer(self, verifier):
        """Test that employee_count must be an integer."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "employee_count": "100",
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("employee_count must be" in err for err in result.errors)

    def test_founded_year_not_integer(self, verifier):
        """Test that founded_year must be an integer."""
        data = {
            "name": "Acme",
            "domains": ["technology"],
            "founded_year": "2010",
        }
        result = verifier.verify(data)
        assert not result.ok
        assert any("founded_year must be" in err for err in result.errors)

    def test_valid_with_all_optional_fields(self, verifier):
        """Test validation with all optional fields populated."""
        data = {
            "name": "Acme Corp",
            "domains": ["technology", "consulting"],
            "description": "A tech company",
            "founded_year": 2010,
            "company_size": "large",
            "employee_count": 5000,
            "ownership_type": "public",
            "website": "https://acme.com",
            "headquarters": {
                "city": "San Francisco",
                "state": "CA",
                "country": "USA",
            },
            "industry_classification": {
                "naics": "541511",
                "sic": "7372",
            },
            "technology_signals": [
                {
                    "technology": "Python",
                    "category": "programming",
                    "interest_level": "high",
                    "confidence": 0.95,
                    "signals": ["GitHub repos", "Job postings"],
                    "notes": "Heavy use",
                }
            ],
        }
        result = verifier.verify(data)
        assert result.ok
        assert not result.errors