"""
Verifier registry for managing named CV verifiers.

Similar to the extractor registry, this allows users to choose between
different verification strategies via the CLI.
"""

from __future__ import annotations

from typing import Dict, List, Type, Optional

from .base import CVVerifier


# Global verifier registry
_VERIFIER_REGISTRY: Dict[str, Type[CVVerifier]] = {}


def register_verifier(name: str, verifier_class: Type[CVVerifier]) -> None:
    """
    Register a verifier class in the global registry.
    
    Args:
        name: The name to register the verifier under (e.g., "data-verifier")
        verifier_class: The verifier class to register
    """
    _VERIFIER_REGISTRY[name] = verifier_class


def get_verifier(name: str, **kwargs) -> Optional[CVVerifier]:
    """
    Get a verifier instance by name.
    
    Args:
        name: The verifier name (e.g., "data-verifier", "cv-schema-verifier")
        **kwargs: Arguments to pass to the verifier constructor
    
    Returns:
        Verifier instance, or None if not found
    """
    verifier_class = _VERIFIER_REGISTRY.get(name)
    if verifier_class:
        return verifier_class(**kwargs)
    return None


def list_verifiers() -> List[Dict[str, str]]:
    """
    List all registered verifiers with their descriptions.
    
    Returns:
        List of dicts with 'name' and 'description' keys
    """
    verifiers = []
    for name, verifier_class in _VERIFIER_REGISTRY.items():
        # Try to get description from class docstring
        description = verifier_class.__doc__ or "No description available"
        # Extract first line of docstring
        description = description.strip().split('\n')[0]
        verifiers.append({
            'name': name,
            'description': description
        })
    return sorted(verifiers, key=lambda x: x['name'])


def unregister_verifier(name: str) -> None:
    """
    Unregister a verifier from the global registry.
    
    Args:
        name: The verifier name to unregister
    """
    _VERIFIER_REGISTRY.pop(name, None)


__all__ = [
    "register_verifier",
    "get_verifier",
    "list_verifiers",
    "unregister_verifier",
]
