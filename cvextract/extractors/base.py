"""
Base interface for CV extractors.

Defines the contract for pluggable CV extraction implementations.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict

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
            work: UnitOfWork with input/output paths and config. Implementations
                should read from work.input and write JSON to work.output.

        Returns:
            UnitOfWork with output JSON populated.

        Raises:
            ValueError: If output path is not set
            FileNotFoundError: If the source file does not exist
            Exception: For extraction-specific errors
        """
        ...

    def _write_output_json(self, work: UnitOfWork, data: Dict[str, Any]) -> UnitOfWork:
        if work.output is None:
            raise ValueError("Extraction output path is not set")
        work.output.parent.mkdir(parents=True, exist_ok=True)
        with work.output.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return work
