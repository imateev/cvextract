"""
Renderer registry for managing named CV renderers.

Similar to the extractor registry, this allows users to choose between
different rendering strategies via the CLI.
"""

from __future__ import annotations

from typing import Dict, List, Type, Optional

from .base import CVRenderer

# Global renderer registry
_RENDERER_REGISTRY: Dict[str, Type[CVRenderer]] = {}

def register_renderer(name: str, renderer_class: Type[CVRenderer]) -> None:
    """
    Register a renderer class in the global registry.
    
    Args:
        name: The name to register the renderer under (e.g., "private-internal-renderer")
        renderer_class: The renderer class to register
    """
    _RENDERER_REGISTRY[name] = renderer_class

def get_renderer(name: str, **kwargs) -> Optional[CVRenderer]:
    """
    Get a renderer instance by name.
    
    Args:
        name: The renderer name (e.g., "private-internal-renderer")
        **kwargs: Arguments to pass to the renderer constructor
    
    Returns:
        Renderer instance, or None if not found
    """
    renderer_class = _RENDERER_REGISTRY.get(name)
    if renderer_class:
        return renderer_class(**kwargs)
    return None

def list_renderers() -> List[Dict[str, str]]:
    """
    List all registered renderers with their descriptions.
    
    Returns:
        List of dicts with 'name' and 'description' keys
    """
    renderers = []
    for name, renderer_class in _RENDERER_REGISTRY.items():
        # Try to get description from class docstring
        description = renderer_class.__doc__ or "No description available"
        # Extract first line of docstring
        description = description.strip().split('\n')[0]
        renderers.append({
            'name': name,
            'description': description
        })
    return sorted(renderers, key=lambda x: x['name'])

def unregister_renderer(name: str) -> None:
    """
    Unregister a renderer from the global registry.
    
    Args:
        name: The renderer name to unregister
    """
    _RENDERER_REGISTRY.pop(name, None)

__all__ = [
    "register_renderer",
    "get_renderer",
    "list_renderers",
    "unregister_renderer",
]
