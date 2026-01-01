"""
OpenAI-based company research adjuster.

Adjusts CV data based on target company research using OpenAI.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from .base import CVAdjuster
from ..ml_adjustment import MLAdjuster


class OpenAICompanyResearchAdjuster(CVAdjuster):
    """
    Adjuster that uses OpenAI to tailor CV based on company research.
    
    This adjuster researches a target company and adjusts the CV to highlight
    relevant experience, skills, and technologies.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        """
        Initialize the adjuster.
        
        Args:
            model: OpenAI model to use (default: "gpt-4o-mini")
            api_key: Optional OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self._model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._adjuster = MLAdjuster(model=self._model, api_key=self._api_key)
    
    def name(self) -> str:
        """Return adjuster name."""
        return "openai-company-research"
    
    def description(self) -> str:
        """Return adjuster description."""
        return "Adjusts CV based on target company research using OpenAI"
    
    def validate_params(self, **kwargs) -> None:
        """
        Validate required parameters.
        
        Args:
            **kwargs: Must contain 'customer_url'
        
        Raises:
            ValueError: If customer_url is missing
        """
        if 'customer_url' not in kwargs or not kwargs['customer_url']:
            raise ValueError(f"Adjuster '{self.name()}' requires 'customer-url' parameter")
    
    def adjust(self, cv_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Adjust CV based on company research.
        
        Args:
            cv_data: The CV data to adjust
            **kwargs: Must contain 'customer_url', optional 'cache_path'
        
        Returns:
            Adjusted CV data
        """
        self.validate_params(**kwargs)
        
        customer_url = kwargs['customer_url']
        cache_path = kwargs.get('cache_path')
        
        return self._adjuster.adjust(cv_data, customer_url, cache_path=cache_path)
