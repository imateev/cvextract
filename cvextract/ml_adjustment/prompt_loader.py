"""
Utility for loading prompt templates from Markdown files.

This module provides a simple, cross-platform way to load prompts from the
prompts/ subdirectory using pathlib. Searches in both adjuster and ml_adjustment
directories with fallback behavior.

Search order:
1. Adjuster prompts directory: cvextract/adjusters/prompts/{prompt_name}.md
2. ML adjustment prompts directory: cvextract/ml_adjustment/prompts/{prompt_name}.md
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

# Paths to prompts directories
_ADJUSTER_PROMPTS_DIR = Path(__file__).parent.parent / "adjusters" / "prompts"
_ML_PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(prompt_name: str) -> Optional[str]:
    """
    Load a prompt template from a Markdown file.
    
    Searches in adjuster prompts folder first, then falls back to ml_adjustment folder.
    
    Args:
        prompt_name: Name of the prompt file (without .md extension)
    
    Returns:
        The prompt text, or None if the file doesn't exist or can't be read
    
    Example:
        >>> cv_system = load_prompt("cv_extraction_system")
        >>> if cv_system:
        ...     print(cv_system[:50])
    """
    # Try adjuster prompts folder first
    adjuster_prompt_path = _ADJUSTER_PROMPTS_DIR / f"{prompt_name}.md"
    if adjuster_prompt_path.exists():
        try:
            return adjuster_prompt_path.read_text(encoding="utf-8")
        except Exception:
            return None
    
    # Fall back to ml_adjustment prompts folder
    ml_prompt_path = _ML_PROMPTS_DIR / f"{prompt_name}.md"
    try:
        return ml_prompt_path.read_text(encoding="utf-8")
    except Exception:
        return None


def format_prompt(prompt_name: str, **kwargs) -> Optional[str]:
    """
    Load a prompt template and format it with the provided variables.
    
    Args:
        prompt_name: Name of the prompt file (without .md extension)
        **kwargs: Variables to substitute in the prompt template
    
    Returns:
        The formatted prompt text, or None if the file doesn't exist or can't be read
    
    Example:
        >>> prompt = format_prompt("website_analysis_prompt", 
        ...                        customer_url="https://example.com",
        ...                        schema="{}")
        >>> if prompt:
        ...     print(prompt[:50])
    """
    template = load_prompt(prompt_name)
    if template is None:
        return None
    
    try:
        return template.format(**kwargs)
    except Exception:
        return None
