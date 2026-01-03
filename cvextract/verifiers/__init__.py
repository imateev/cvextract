"""
CV verification interfaces and implementations.

This module provides pluggable and interchangeable CV verifiers.
"""

from .base import CVVerifier
from .data_verifier import ExtractedDataVerifier
from .comparison_verifier import RoundtripVerifier, FileRoundtripVerifier
from .schema_verifier import CVSchemaVerifier
from .company_profile_verifier import CompanyProfileVerifier
from .verifier_registry import (
    register_verifier,
    get_verifier,
    list_verifiers,
)


 # Register built-in verifiers
register_verifier("private-internal-verifier", ExtractedDataVerifier)
register_verifier("roundtrip-verifier", RoundtripVerifier)
register_verifier("file-roundtrip-verifier", FileRoundtripVerifier)
register_verifier("cv-schema-verifier", CVSchemaVerifier)
register_verifier("company-profile-verifier", CompanyProfileVerifier)


__all__ = [
    "CVVerifier",
    "register_verifier",
    "get_verifier",
    "list_verifiers",
]
