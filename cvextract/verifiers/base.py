"""
Base interface for CV verifiers.

Defines the contract for pluggable CV verification implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..shared import UnitOfWork, VerificationResult


class CVVerifier(ABC):
    """
    Abstract base class for CV verifiers.

    Implementations of this interface can verify CV data in different ways,
    such as schema validation, completeness checks, or data comparisons.
    """

    @abstractmethod
    def verify(self, work: UnitOfWork) -> VerificationResult:
        """
        Verify CV data and return a verification result.

        Args:
            work: UnitOfWork containing the current pipeline state and paths

        Returns:
            VerificationResult with errors and warnings (ok is derived from errors)

        Raises:
            Exception: For verification-specific errors
        """
        ...
