"""Tests for extractor registry functionality."""

import pytest
from pathlib import Path
from unittest.mock import patch
from cvextract.extractors import (
    CVExtractor,
    get_extractor,
    list_extractors,
    register_extractor,
)


class TestExtractorRegistry:
    """Tests for the extractor registry system."""

    def test_list_extractors_returns_built_in_extractors(self):
        """list_extractors() returns the built-in extractors."""
        extractors = list_extractors()
        
        # Should have at least 2 extractors registered
        assert len(extractors) >= 2
        
        # Extract names
        names = [e['name'] for e in extractors]
        
        # Check for built-in extractors
        assert 'private-internal-extractor' in names
        assert 'openai-extractor' in names
        
        # Each should have a description
        for extractor in extractors:
            assert 'name' in extractor
            assert 'description' in extractor
            assert isinstance(extractor['name'], str)
            assert isinstance(extractor['description'], str)
            assert len(extractor['description']) > 0

    def test_get_extractor_returns_private_internal(self):
        """get_extractor() returns private-internal-extractor instance."""
        extractor = get_extractor('private-internal-extractor')
        
        assert extractor is not None
        assert isinstance(extractor, CVExtractor)

    def test_get_extractor_returns_openai(self):
        """get_extractor() returns openai-extractor instance."""
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = get_extractor('openai-extractor')
            
            assert extractor is not None
            assert isinstance(extractor, CVExtractor)

    def test_get_extractor_returns_none_for_unknown(self):
        """get_extractor() returns None for unknown extractor name."""
        extractor = get_extractor('nonexistent-extractor')
        
        assert extractor is None

    def test_get_extractor_with_kwargs(self):
        """get_extractor() passes kwargs to extractor constructor."""
        # OpenAI extractor accepts model parameter
        with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
            extractor = get_extractor('openai-extractor', model='gpt-4')
            
            assert extractor is not None
            assert hasattr(extractor, 'model')
            assert extractor.model == 'gpt-4'

    def test_register_custom_extractor(self):
        """register_extractor() allows registering custom extractors."""
        
        class CustomExtractor(CVExtractor):
            """Custom test extractor for testing."""
            
            def extract(self, source: Path):
                return {
                    "identity": {
                        "title": "Custom",
                        "full_name": "Custom Extractor",
                        "first_name": "Custom",
                        "last_name": "Extractor"
                    },
                    "sidebar": {},
                    "overview": "Custom overview",
                    "experiences": []
                }
        
        # Register custom extractor
        register_extractor('custom-test-extractor', CustomExtractor)
        
        # Should now be in the list
        extractors = list_extractors()
        names = [e['name'] for e in extractors]
        assert 'custom-test-extractor' in names
        
        # Should be retrievable
        extractor = get_extractor('custom-test-extractor')
        assert extractor is not None
        assert isinstance(extractor, CustomExtractor)
        
        # Should work
        result = extractor.extract(Path('/any/path'))
        assert result['identity']['title'] == 'Custom'

    def test_list_extractors_is_sorted(self):
        """list_extractors() returns extractors sorted by name."""
        extractors = list_extractors()
        names = [e['name'] for e in extractors]
        
        # Should be sorted
        assert names == sorted(names)
