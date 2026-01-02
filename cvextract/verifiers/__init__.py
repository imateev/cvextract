"""
CV verification interfaces and implementations.

This module provides pluggable and interchangeable CV verifiers.
"""

from .base import CVVerifier
from .data_verifier import ExtractedDataVerifier
from .comparison_verifier import ComparisonVerifier, FileComparisonVerifier
from .schema_verifier import SchemaVerifier

__all__ = [
    "CVVerifier",
    "ExtractedDataVerifier",
    "ComparisonVerifier",
    "FileComparisonVerifier",
    "SchemaVerifier",
]
