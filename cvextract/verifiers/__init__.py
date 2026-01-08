"""
CV verification interfaces and implementations.

This module provides pluggable and interchangeable CV verifiers.
"""

from .base import CVVerifier
from .default_expected_cv_data_verifier import ExtractedDataVerifier
from .roundtrip_verifier import RoundtripVerifier
from .default_cv_schema_verifier import CVSchemaVerifier
from .verifier_registry import (
    register_verifier,
    get_verifier,
    list_verifiers,
)


# Register built-in verifiers
register_verifier("private-internal-verifier", ExtractedDataVerifier)
register_verifier("roundtrip-verifier", RoundtripVerifier)
register_verifier("cv-schema-verifier", CVSchemaVerifier)


__all__ = [
    "CVVerifier",
    "register_verifier",
    "get_verifier",
    "list_verifiers",
]
