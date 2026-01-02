"""
Extractor registry for managing named CV extractors.

Similar to the adjuster registry, this allows users to choose between
different extraction strategies via the CLI.
"""

from __future__ import annotations

from typing import Dict, List, Type, Optional

from .base import CVExtractor


# Global extractor registry
_EXTRACTOR_REGISTRY: Dict[str, Type[CVExtractor]] = {}


def register_extractor(name: str, extractor_class: Type[CVExtractor]) -> None:
    """
    Register an extractor class in the global registry.
    
    Args:
        name: The name to register the extractor under (e.g., "openai-extractor")
        extractor_class: The extractor class to register
    """
    _EXTRACTOR_REGISTRY[name] = extractor_class


def get_extractor(name: str, **kwargs) -> Optional[CVExtractor]:
    """
    Get an extractor instance by name.
    
    Args:
        name: The extractor name (e.g., "openai-extractor", "private-internal-extractor")
        **kwargs: Arguments to pass to the extractor constructor
    
    Returns:
        Extractor instance, or None if not found
    """
    extractor_class = _EXTRACTOR_REGISTRY.get(name)
    if extractor_class:
        return extractor_class(**kwargs)
    return None


def list_extractors() -> List[Dict[str, str]]:
    """
    List all registered extractors with their descriptions.
    
    Returns:
        List of dicts with 'name' and 'description' keys
    """
    extractors = []
    for name, extractor_class in _EXTRACTOR_REGISTRY.items():
        # Try to get description from class docstring
        description = extractor_class.__doc__ or "No description available"
        # Extract first line of docstring
        description = description.strip().split('\n')[0]
        extractors.append({
            'name': name,
            'description': description
        })
    return sorted(extractors, key=lambda x: x['name'])


def unregister_extractor(name: str) -> None:
    """
    Unregister an extractor from the global registry.
    
    Args:
        name: The extractor name to unregister
    """
    _EXTRACTOR_REGISTRY.pop(name, None)


__all__ = [
    "register_extractor",
    "get_extractor",
    "list_extractors",
    "unregister_extractor",
]
