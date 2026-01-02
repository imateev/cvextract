"""Tests for verifier registry functionality."""

import pytest
from pathlib import Path
from cvextract.verifiers import (
    CVVerifier,
    get_verifier,
    list_verifiers,
    register_verifier,
)
from cvextract.verifiers.verifier_registry import unregister_verifier
from cvextract.shared import VerificationResult


class TestVerifierRegistry:
    """Tests for the verifier registry system."""

    def test_list_verifiers_returns_built_in_verifiers(self):
        """list_verifiers() returns the built-in verifiers."""
        verifiers = list_verifiers()
        
        # Should have at least 4 verifiers registered
        assert len(verifiers) >= 4
        
        # Extract names
        names = [v['name'] for v in verifiers]
        
        # Check for built-in verifiers
        assert 'data-verifier' in names
        assert 'comparison-verifier' in names
        assert 'file-comparison-verifier' in names
        assert 'schema-verifier' in names
        
        # Each should have a description
        for verifier in verifiers:
            assert 'name' in verifier
            assert 'description' in verifier
            assert isinstance(verifier['name'], str)
            assert isinstance(verifier['description'], str)
            assert len(verifier['description']) > 0

    def test_get_verifier_returns_data_verifier(self):
        """get_verifier() returns data-verifier instance."""
        verifier = get_verifier('data-verifier')
        
        assert verifier is not None
        assert isinstance(verifier, CVVerifier)

    def test_get_verifier_returns_comparison_verifier(self):
        """get_verifier() returns comparison-verifier instance."""
        verifier = get_verifier('comparison-verifier')
        
        assert verifier is not None
        assert isinstance(verifier, CVVerifier)

    def test_get_verifier_returns_file_comparison_verifier(self):
        """get_verifier() returns file-comparison-verifier instance."""
        verifier = get_verifier('file-comparison-verifier')
        
        assert verifier is not None
        assert isinstance(verifier, CVVerifier)

    def test_get_verifier_returns_schema_verifier(self):
        """get_verifier() returns schema-verifier instance."""
        verifier = get_verifier('schema-verifier')
        
        assert verifier is not None
        assert isinstance(verifier, CVVerifier)

    def test_get_verifier_returns_none_for_unknown(self):
        """get_verifier() returns None for unknown verifier name."""
        verifier = get_verifier('nonexistent-verifier')
        
        assert verifier is None

    def test_get_verifier_with_kwargs(self):
        """get_verifier() passes kwargs to verifier constructor."""
        # SchemaVerifier accepts schema_path parameter
        schema_path = Path('/tmp/test_schema.json')
        verifier = get_verifier('schema-verifier', schema_path=schema_path)
        
        assert verifier is not None
        assert hasattr(verifier, 'schema_path')
        assert verifier.schema_path == schema_path

    def test_register_custom_verifier(self):
        """register_verifier() allows registering custom verifiers."""
        
        class CustomVerifier(CVVerifier):
            """Custom test verifier for testing."""
            
            def verify(self, data, **kwargs):
                return VerificationResult(
                    ok=True,
                    errors=[],
                    warnings=["custom-verifier"]
                )
        
        # Register custom verifier
        register_verifier('custom-test-verifier', CustomVerifier)
        
        try:
            # Should now be in the list
            verifiers = list_verifiers()
            names = [v['name'] for v in verifiers]
            assert 'custom-test-verifier' in names
            
            # Should be retrievable
            verifier = get_verifier('custom-test-verifier')
            assert verifier is not None
            assert isinstance(verifier, CustomVerifier)
            
            # Should work
            result = verifier.verify({})
            assert result.ok is True
            assert 'custom-verifier' in result.warnings
        finally:
            # Clean up the custom verifier
            unregister_verifier('custom-test-verifier')

    def test_list_verifiers_is_sorted(self):
        """list_verifiers() returns verifiers sorted by name."""
        verifiers = list_verifiers()
        names = [v['name'] for v in verifiers]
        
        # Should be sorted
        assert names == sorted(names)
