"""
Base interface for CV adjusters.

Defines the contract for pluggable CV adjustment implementations.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict

from ..pipeline_helpers import UnitOfWork


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
    def adjust(self, work: UnitOfWork, **kwargs) -> Dict[str, Any]:
        """
        Adjust CV data based on the adjuster's specific logic.
        
        Args:
            work: UnitOfWork with input/output paths and config. Adjusters should load JSON from work.input
            **kwargs: Adjuster-specific parameters (e.g., customer_url, job_url, etc.)
        
        Returns:
            Adjusted CV data dictionary. On error, should return original data.
        
        Raises:
            ValueError: If required parameters are missing or invalid
        """
        ...

    def _load_input_json(self, work: UnitOfWork) -> Dict[str, Any]:
        with work.input.open("r", encoding="utf-8") as f:
            return json.load(f)
    
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
