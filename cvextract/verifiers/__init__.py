"""
CV verification interfaces and implementations.

This module provides pluggable and interchangeable CV verifiers with a registry system.
"""

from .base import CVVerifier
from .data_verifier import ExtractedDataVerifier
from .comparison_verifier import ComparisonVerifier, FileComparisonVerifier
from .schema_verifier import SchemaVerifier
from .verifier_registry import (
    register_verifier,
    get_verifier,
    list_verifiers,
)


 # Register built-in verifiers
register_verifier("private-internal-verifier", ExtractedDataVerifier)
register_verifier("comparison-verifier", ComparisonVerifier)
register_verifier("file-comparison-verifier", FileComparisonVerifier)
register_verifier("schema-verifier", SchemaVerifier)


__all__ = [
    "CVVerifier",
    "ExtractedDataVerifier",
    "ComparisonVerifier",
    "FileComparisonVerifier",
    "SchemaVerifier",
    "register_verifier",
    "get_verifier",
    "list_verifiers",
]
