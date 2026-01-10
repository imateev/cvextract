"""
Base interface for CV extractors.

Defines the contract for pluggable CV extraction implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..shared import UnitOfWork


class CVExtractor(ABC):
    """
    Abstract base class for CV extractors.

    Implementations of this interface can extract structured CV data
    from various input formats and return a standardized dictionary
    conforming to the CV schema.
    """

    @abstractmethod
    def extract(self, work: UnitOfWork) -> UnitOfWork:
        """
        Extract structured CV data from the given work unit.

        Args:
            work: UnitOfWork with Extract step input/output paths and config.
                Implementations should read from the Extract step input and
                write JSON to the Extract step output.

        Returns:
            UnitOfWork with output JSON populated.

        Raises:
            ValueError: If output path is not set
            FileNotFoundError: If the source file does not exist
            Exception: For extraction-specific errors
        """
        ...
