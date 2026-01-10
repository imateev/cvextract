"""Tests for verifier registry functionality."""

import json
from pathlib import Path

import pytest

from cvextract.cli_config import UserConfig
from cvextract.shared import StepName, UnitOfWork
from cvextract.verifiers import (
    CVVerifier,
    get_verifier,
    list_verifiers,
    register_verifier,
)

# Note: unregister_verifier is not in public API, import from registry module for testing
from cvextract.verifiers.verifier_registry import unregister_verifier


def _make_work(tmp_path):
    path = tmp_path / "data.json"
    path.write_text(json.dumps({}), encoding="utf-8")
    work = UnitOfWork(config=UserConfig(target_dir=tmp_path))
    work.set_step_paths(StepName.Extract, input_path=path, output_path=path)
    work.current_step = StepName.Extract
    work.ensure_step_status(StepName.Extract)
    return work


class TestVerifierRegistry:
    """Tests for the verifier registry system."""

    def test_list_verifiers_returns_built_in_verifiers(self):
        """list_verifiers() returns the built-in verifiers."""
        verifiers = list_verifiers()

        # Should have at least 3 verifiers registered
        assert len(verifiers) >= 3

        # Extract names
        names = [v["name"] for v in verifiers]

        # Check for built-in verifiers
        assert "default-extract-verifier" in names
        assert "roundtrip-verifier" in names
        assert "cv-schema-verifier" in names

        # Each should have a description
        for verifier in verifiers:
            assert "name" in verifier
            assert "description" in verifier
            assert isinstance(verifier["name"], str)
            assert isinstance(verifier["description"], str)
            assert len(verifier["description"]) > 0

    def test_get_verifier_returns_data_verifier(self):
        """get_verifier() returns default-extract-verifier instance."""
        verifier = get_verifier("default-extract-verifier")

        assert verifier is not None
        assert isinstance(verifier, CVVerifier)

    def test_get_verifier_returns_roundtrip_verifier(self):
        """get_verifier() returns roundtrip-verifier instance."""
        verifier = get_verifier("roundtrip-verifier")

        assert verifier is not None
        assert isinstance(verifier, CVVerifier)

    def test_get_verifier_returns_schema_verifier(self):
        """get_verifier() returns cv-schema-verifier instance."""
        verifier = get_verifier("cv-schema-verifier")

        assert verifier is not None
        assert isinstance(verifier, CVVerifier)

    def test_get_verifier_returns_none_for_unknown(self):
        """get_verifier() returns None for unknown verifier name."""
        verifier = get_verifier("nonexistent-verifier")

        assert verifier is None

    def test_get_verifier_with_kwargs(self):
        """get_verifier() passes kwargs to verifier constructor."""
        # CVSchemaVerifier accepts schema_path parameter
        schema_path = Path("/tmp/test_schema.json")
        verifier = get_verifier("cv-schema-verifier", schema_path=schema_path)

        assert verifier is not None
        assert hasattr(verifier, "schema_path")
        assert verifier.schema_path == schema_path

    def test_register_custom_verifier(self, tmp_path):
        """register_verifier() allows registering custom verifiers."""

        class CustomVerifier(CVVerifier):
            """Custom test verifier for testing."""

            def verify(self, work: UnitOfWork):
                return self._record(work, [], ["custom-verifier"])

        # Register custom verifier
        register_verifier("custom-test-verifier", CustomVerifier)

        try:
            # Should now be in the list
            verifiers = list_verifiers()
            names = [v["name"] for v in verifiers]
            assert "custom-test-verifier" in names

            # Should be retrievable
            verifier = get_verifier("custom-test-verifier")
            assert verifier is not None
            assert isinstance(verifier, CustomVerifier)

            # Should work
            work = _make_work(tmp_path)
            result = verifier.verify(work)
            status = result.step_states[StepName.Extract]
            assert "custom-verifier" in status.warnings
        finally:
            # Clean up the custom verifier
            unregister_verifier("custom-test-verifier")

    def test_list_verifiers_is_sorted(self):
        """list_verifiers() returns verifiers sorted by name."""
        verifiers = list_verifiers()
        names = [v["name"] for v in verifiers]

        # Should be sorted
        assert names == sorted(names)
