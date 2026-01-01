"""
CV adjustment interfaces and implementations.

This module provides pluggable and interchangeable CV adjusters with a registry system.
"""

from __future__ import annotations

from typing import Dict, List, Type, Optional

from .base import CVAdjuster
from .openai_company_research_adjuster import OpenAICompanyResearchAdjuster
from .openai_job_specific_adjuster import OpenAIJobSpecificAdjuster


# Global adjuster registry
_ADJUSTER_REGISTRY: Dict[str, Type[CVAdjuster]] = {}


def register_adjuster(adjuster_class: Type[CVAdjuster]) -> None:
    """
    Register an adjuster class in the global registry.
    
    Args:
        adjuster_class: The adjuster class to register
    """
    # Create temporary instance to get name
    instance = adjuster_class()
    name = instance.name()
    _ADJUSTER_REGISTRY[name] = adjuster_class


def get_adjuster(name: str, **kwargs) -> Optional[CVAdjuster]:
    """
    Get an adjuster instance by name.
    
    Args:
        name: The adjuster name (e.g., "openai-company-research")
        **kwargs: Arguments to pass to the adjuster constructor
    
    Returns:
        Adjuster instance, or None if not found
    """
    adjuster_class = _ADJUSTER_REGISTRY.get(name)
    if adjuster_class:
        return adjuster_class(**kwargs)
    return None


def list_adjusters() -> List[Dict[str, str]]:
    """
    List all registered adjusters with their descriptions.
    
    Returns:
        List of dicts with 'name' and 'description' keys
    """
    adjusters = []
    for name, adjuster_class in _ADJUSTER_REGISTRY.items():
        instance = adjuster_class()
        adjusters.append({
            'name': name,
            'description': instance.description()
        })
    return sorted(adjusters, key=lambda x: x['name'])


# Register built-in adjusters
register_adjuster(OpenAICompanyResearchAdjuster)
register_adjuster(OpenAIJobSpecificAdjuster)


__all__ = [
    "CVAdjuster",
    "OpenAICompanyResearchAdjuster",
    "OpenAIJobSpecificAdjuster",
    "register_adjuster",
    "get_adjuster",
    "list_adjusters",
]
