"""
Verification helpers for extracted and rendered CV data.

This module provides backward-compatible wrapper functions that use
the new pluggable verifier architecture internally.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from .shared import VerificationResult
from .verifiers import ExtractedDataVerifier, ComparisonVerifier, FileComparisonVerifier


# Singleton instances for efficiency
_extracted_data_verifier = ExtractedDataVerifier()
_comparison_verifier = ComparisonVerifier()
_file_comparison_verifier = FileComparisonVerifier()


def verify_extracted_data(data: dict) -> VerificationResult:
    """
    Verify extracted CV data for completeness and validity.
    
    This is a compatibility wrapper around ExtractedDataVerifier.
    
    Args:
        data: Dictionary containing extracted CV data
    
    Returns:
        VerificationResult with validation results
    """
    return _extracted_data_verifier.verify(data)


def compare_data_structures(original: Dict[str, Any], new: Dict[str, Any]) -> VerificationResult:
    """
    Deep-compare two data structures and report mismatches as errors.
    
    This is a compatibility wrapper around ComparisonVerifier.
    
    Args:
        original: Source CV data dictionary
        new: Target CV data dictionary to compare against
    
    Returns:
        VerificationResult with comparison results
    """
    return _comparison_verifier.verify(original, target_data=new)


def compare_json_files(original_json: Path, roundtrip_json: Path) -> VerificationResult:
    """
    Compare two CV data JSON files.
    
    This is a compatibility wrapper around FileComparisonVerifier.
    
    Args:
        original_json: Path to source JSON file
        roundtrip_json: Path to target JSON file
    
    Returns:
        VerificationResult with comparison results
    """
    return _file_comparison_verifier.verify(
        {},
        source_file=original_json,
        target_file=roundtrip_json
    )
