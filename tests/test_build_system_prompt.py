"""Tests for _build_system_prompt function in adjuster.py."""

from cvextract.ml_adjustment.adjuster import _build_system_prompt


class TestBuildSystemPrompt:
    """Tests for _build_system_prompt function."""

    def test_build_system_prompt_with_full_data(self):
        """Test building system prompt with all data fields."""
        research_data = {
            "name": "TechCorp",
            "domains": ["Technology", "SaaS"],
            "description": "A leading tech company",
            "acquisition_history": [
                {
                    "owner": "BigTech Corp",
                    "year": 2020,
                    "notes": "Acquired for $100M"
                },
                {
                    "owner": "StartupVentures",
                    "year": 2015,
                    "notes": ""
                }
            ],
            "rebranded_from": ["OldName Systems", "Legacy Corp"],
            "owned_products": [
                {
                    "name": "SuperApp",
                    "category": "SaaS",
                    "description": "Project management tool"
                },
                {
                    "name": "DataHub",
                    "category": "software",
                    "description": ""
                }
            ],
            "used_products": [
                {
                    "name": "Salesforce",
                    "category": "CRM",
                    "purpose": "Customer relationship management"
                },
                {
                    "name": "AWS",
                    "category": "cloud platform",
                    "purpose": ""
                }
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "TechCorp" in prompt
        assert "Technology, SaaS" in prompt
        assert "Acquisition History" in prompt
        assert "BigTech Corp" in prompt
        assert "2020" in prompt
        assert "$100M" in prompt
        assert "Previous Names" in prompt
        assert "OldName Systems" in prompt
        assert "Owned Products/Services" in prompt
        assert "SuperApp" in prompt
        assert "SaaS" in prompt
        assert "Products/Tools Used by Company" in prompt
        assert "Salesforce" in prompt
        assert "CRM" in prompt

    def test_build_system_prompt_with_acquisition_history_missing_year_and_notes(self):
        """Test acquisition history with missing year and notes."""
        research_data = {
            "name": "Company",
            "domains": [],
            "acquisition_history": [
                {
                    "owner": "OldOwner",
                    # No year or notes
                }
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "OldOwner" in prompt
        assert "Acquisition History" in prompt

    def test_build_system_prompt_with_acquisition_history_missing_owner(self):
        """Test acquisition history with missing owner."""
        research_data = {
            "name": "Company",
            "domains": [],
            "acquisition_history": [
                {
                    "year": 2020,
                    "notes": "Some notes"
                }
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "Unknown" in prompt
        assert "2020" in prompt
        assert "Some notes" in prompt

    def test_build_system_prompt_with_rebranding_history(self):
        """Test rebranding history in prompt."""
        research_data = {
            "name": "NewName",
            "domains": [],
            "rebranded_from": ["OldName", "VeryOldName"]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "Previous Names" in prompt
        assert "OldName" in prompt
        assert "VeryOldName" in prompt

    def test_build_system_prompt_with_owned_products_missing_fields(self):
        """Test owned products with missing optional fields."""
        research_data = {
            "name": "Company",
            "domains": [],
            "owned_products": [
                {
                    "name": "Product1",
                    # No category or description
                },
                {
                    "name": "Product2",
                    "category": "Type1"
                    # No description
                }
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "Owned Products/Services" in prompt
        assert "Product1" in prompt
        assert "Product2" in prompt
        assert "Type1" in prompt

    def test_build_system_prompt_with_owned_products_missing_name(self):
        """Test owned products with missing name."""
        research_data = {
            "name": "Company",
            "domains": [],
            "owned_products": [
                {
                    "category": "Type1",
                    "description": "A product"
                }
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "Unknown" in prompt
        assert "Type1" in prompt
        assert "A product" in prompt

    def test_build_system_prompt_with_used_products_missing_fields(self):
        """Test used products with missing optional fields."""
        research_data = {
            "name": "Company",
            "domains": [],
            "used_products": [
                {
                    "name": "Tool1",
                    # No category or purpose
                },
                {
                    "name": "Tool2",
                    "category": "Cloud",
                    # No purpose
                }
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "Products/Tools Used by Company" in prompt
        assert "Tool1" in prompt
        assert "Tool2" in prompt
        assert "Cloud" in prompt

    def test_build_system_prompt_with_used_products_missing_name(self):
        """Test used products with missing name."""
        research_data = {
            "name": "Company",
            "domains": [],
            "used_products": [
                {
                    "category": "Platform",
                    "purpose": "Data storage"
                }
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "Unknown" in prompt
        assert "Platform" in prompt
        assert "Data storage" in prompt

    def test_build_system_prompt_minimal_data(self):
        """Test with minimal research data."""
        research_data = {
            "name": "Company"
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "Company" in prompt

    def test_build_system_prompt_empty_collections(self):
        """Test with empty acquisition, products, rebranding lists."""
        research_data = {
            "name": "Company",
            "domains": ["Tech"],
            "acquisition_history": [],
            "rebranded_from": [],
            "owned_products": [],
            "used_products": []
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "Company" in prompt
        # Should NOT contain these headers since lists are empty
        assert "Acquisition History" not in prompt
        assert "Previous Names" not in prompt
        assert "Owned Products" not in prompt
        assert "Products/Tools Used" not in prompt

    def test_build_system_prompt_acquisition_history_with_year_and_notes(self):
        """Test acquisition history formatting with both year and notes."""
        research_data = {
            "name": "Company",
            "domains": [],
            "acquisition_history": [
                {
                    "owner": "Acquirer",
                    "year": 2025,
                    "notes": "Important acquisition"
                }
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "Acquirer (2025): Important acquisition" in prompt

    def test_build_system_prompt_acquisition_history_with_year_only(self):
        """Test acquisition history formatting with year but no notes."""
        research_data = {
            "name": "Company",
            "domains": [],
            "acquisition_history": [
                {
                    "owner": "Acquirer",
                    "year": 2025,
                    "notes": ""
                }
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "Acquirer (2025)" in prompt
        assert "Acquirer (2025):" not in prompt  # No colon without notes

    def test_build_system_prompt_multiple_acquisitions(self):
        """Test multiple acquisitions are all included."""
        research_data = {
            "name": "Company",
            "domains": [],
            "acquisition_history": [
                {"owner": "First", "year": 2020, "notes": "First"},
                {"owner": "Second", "year": 2022, "notes": "Second"},
                {"owner": "Third", "year": 2024, "notes": "Third"}
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "First" in prompt
        assert "Second" in prompt
        assert "Third" in prompt
        assert "2020" in prompt
        assert "2022" in prompt
        assert "2024" in prompt

    def test_build_system_prompt_owned_products_with_all_fields(self):
        """Test owned products formatting with all fields."""
        research_data = {
            "name": "Company",
            "domains": [],
            "owned_products": [
                {
                    "name": "ProductX",
                    "category": "SaaS",
                    "description": "Excellent tool"
                }
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "ProductX (SaaS): Excellent tool" in prompt

    def test_build_system_prompt_used_products_with_all_fields(self):
        """Test used products formatting with all fields."""
        research_data = {
            "name": "Company",
            "domains": [],
            "used_products": [
                {
                    "name": "ToolY",
                    "category": "Cloud",
                    "purpose": "Hosting"
                }
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "ToolY (Cloud): Hosting" in prompt

    def test_build_system_prompt_with_related_companies(self):
        """Test related companies in prompt."""
        research_data = {
            "name": "Company",
            "domains": [],
            "related_companies": [
                {
                    "name": "TechPartner Inc",
                    "relationship_type": "partner",
                    "description": "Strategic technology partnership"
                },
                {
                    "name": "DataSupply Corp",
                    "relationship_type": "supplier",
                    "description": ""
                }
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "Related Companies & Partnerships" in prompt
        assert "TechPartner Inc (partner): Strategic technology partnership" in prompt
        assert "DataSupply Corp (supplier)" in prompt

    def test_build_system_prompt_with_related_companies_missing_fields(self):
        """Test related companies with missing optional fields."""
        research_data = {
            "name": "Company",
            "domains": [],
            "related_companies": [
                {
                    "name": "Partner1",
                    # No relationship_type or description
                },
                {
                    "name": "Partner2",
                    "relationship_type": "strategic_alliance"
                    # No description
                }
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "Related Companies & Partnerships" in prompt
        assert "Partner1" in prompt
        assert "Partner2 (strategic_alliance)" in prompt

    def test_build_system_prompt_with_related_companies_missing_name(self):
        """Test related companies with missing name."""
        research_data = {
            "name": "Company",
            "domains": [],
            "related_companies": [
                {
                    "relationship_type": "investor",
                    "description": "Venture capital investor"
                }
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "Unknown (investor): Venture capital investor" in prompt

    def test_build_system_prompt_multiple_related_companies(self):
        """Test multiple related companies are all included."""
        research_data = {
            "name": "Company",
            "domains": [],
            "related_companies": [
                {"name": "Partner1", "relationship_type": "partner"},
                {"name": "Supplier1", "relationship_type": "supplier"},
                {"name": "Customer1", "relationship_type": "customer"}
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "Partner1" in prompt
        assert "Supplier1" in prompt
        assert "Customer1" in prompt

    def test_build_system_prompt_empty_related_companies(self):
        """Test with empty related_companies list."""
        research_data = {
            "name": "Company",
            "domains": [],
            "related_companies": []
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        # Should NOT contain this header since list is empty
        assert "Related Companies & Partnerships" not in prompt

    def test_build_system_prompt_all_relationship_types(self):
        """Test all relationship type variations."""
        research_data = {
            "name": "Company",
            "domains": [],
            "related_companies": [
                {"name": "Partner", "relationship_type": "partner"},
                {"name": "Supplier", "relationship_type": "supplier"},
                {"name": "Customer", "relationship_type": "customer"},
                {"name": "Investor", "relationship_type": "investor"},
                {"name": "Sub", "relationship_type": "subsidiary"},
                {"name": "Parent", "relationship_type": "parent"},
                {"name": "Alliance", "relationship_type": "strategic_alliance"}
            ]
        }
        
        prompt = _build_system_prompt(research_data)
        
        assert prompt is not None
        assert "(partner)" in prompt
        assert "(supplier)" in prompt
        assert "(customer)" in prompt
        assert "(investor)" in prompt
        assert "(subsidiary)" in prompt
        assert "(parent)" in prompt
        assert "(strategic_alliance)" in prompt

