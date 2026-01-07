"""
Base interface for CV verifiers.

Defines the contract for pluggable CV verification implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from ..shared import VerificationResult


class CVVerifier(ABC):
    """
    Abstract base class for CV verifiers.

    Implementations of this interface can verify CV data in different ways,
    such as schema validation, completeness checks, or data comparisons.
    """

    @abstractmethod
    def verify(self, data: Dict[str, Any], **kwargs) -> VerificationResult:
        """
        Verify CV data and return a verification result.

        Args:
            data: Dictionary containing CV data to verify
            **kwargs: Additional verification-specific parameters

        Returns:
            VerificationResult with ok status, errors, and warnings

        Raises:
            Exception: For verification-specific errors
        """
        ...
