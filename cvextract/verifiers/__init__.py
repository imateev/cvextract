"""
CV verification interfaces and implementations.

This module provides pluggable and interchangeable CV verifiers with a registry system.
"""

from .base import CVVerifier
from .data_verifier import ExtractedDataVerifier
from .comparison_verifier import RoundtripVerifier, FileRoundtripVerifier
from .schema_verifier import SchemaVerifier
from .verifier_registry import (
    register_verifier,
    get_verifier,
    list_verifiers,
)


 # Register built-in verifiers
register_verifier("private-internal-verifier", ExtractedDataVerifier)
register_verifier("roundtrip-verifier", RoundtripVerifier)
register_verifier("file-roundtrip-verifier", FileRoundtripVerifier)
register_verifier("schema-verifier", SchemaVerifier)


__all__ = [
    "CVVerifier",
    "ExtractedDataVerifier",
    "RoundtripVerifier",
    "FileRoundtripVerifier",
    "SchemaVerifier",
    "register_verifier",
    "get_verifier",
    "list_verifiers",
]
