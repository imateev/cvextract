"""
Base interface for CV verifiers.

Defines the contract for pluggable CV verification implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Iterable

from ..shared import UnitOfWork


class CVVerifier(ABC):
    """
    Abstract base class for CV verifiers.

    Implementations of this interface can verify CV data in different ways,
    such as schema validation, completeness checks, or data comparisons.
    """

    @abstractmethod
    def verify(self, work: UnitOfWork) -> UnitOfWork:
        """
        Verify CV data and update the UnitOfWork status.

        Args:
            work: UnitOfWork containing the current pipeline state and paths

        Returns:
            Updated UnitOfWork with verification errors/warnings recorded

        Raises:
            Exception: For verification-specific errors
        """
        ...

    def _record(
        self, work: UnitOfWork, errors: Iterable[str], warnings: Iterable[str]
    ) -> UnitOfWork:
        step = work.resolve_verification_step()
        work.ensure_step_status(step)
        for err in errors:
            work.add_error(step, err)
        for warn in warnings:
            work.add_warning(step, warn)
        return work
