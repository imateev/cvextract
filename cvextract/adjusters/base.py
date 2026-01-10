"""
Base interface for CV adjusters.

Defines the contract for pluggable CV adjustment implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..shared import UnitOfWork


class CVAdjuster(ABC):
    """
    Abstract base class for CV adjusters.

    Implementations of this interface can adjust CV data for various purposes
    such as customer-specific tailoring, job-specific optimization, etc.
    """

    @abstractmethod
    def name(self) -> str:
        """
        Return the unique name/identifier for this adjuster.

        Returns:
            String identifier used in CLI (e.g., "openai-company-research")
        """
        ...

    @abstractmethod
    def description(self) -> str:
        """
        Return a human-readable description of this adjuster.

        Returns:
            String describing what this adjuster does
        """
        ...

    @abstractmethod
    def adjust(self, work: UnitOfWork, **kwargs) -> UnitOfWork:
        """
        Adjust CV data based on the adjuster's specific logic.

        Args:
            work: UnitOfWork with Adjust step input/output paths and config.
                Adjusters should load JSON from the Adjust step input.
            **kwargs: Adjuster-specific parameters (e.g., customer_url, job_url, etc.)

        Returns:
            UnitOfWork with output updated to the transformed JSON file.

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        ...

    def validate_params(self, **kwargs) -> None:
        """
        Validate that required parameters are present.

        Override this method to validate adjuster-specific parameters.

        Args:
            **kwargs: Parameters to validate

        Raises:
            ValueError: If required parameters are missing or invalid
        """
        ...
