"""
CV verification interfaces and implementations.

This module provides pluggable and interchangeable CV verifiers.
"""

from .base import CVVerifier
from .default_expected_cv_data_verifier import DefaultExpectedCvDataVerifier
from .roundtrip_verifier import RoundtripVerifier
from .default_cv_schema_verifier import DefaultCvSchemaVerifier
from .verifier_registry import (
    register_verifier,
    get_verifier,
    list_verifiers,
)


# Register built-in verifiers
register_verifier("default-extract-verifier", DefaultExpectedCvDataVerifier)
register_verifier("roundtrip-verifier", RoundtripVerifier)
register_verifier("cv-schema-verifier", DefaultCvSchemaVerifier)


__all__ = [
    "CVVerifier",
    "register_verifier",
    "get_verifier",
    "list_verifiers",
]
