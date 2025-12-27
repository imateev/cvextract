"""
Utility for loading prompt templates from Markdown files.

This module provides a simple, cross-platform way to load prompts from the
prompts/ subdirectory using pathlib.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

# Path to the prompts directory
_PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(prompt_name: str) -> Optional[str]:
    """
    Load a prompt template from a Markdown file.
    
    Args:
        prompt_name: Name of the prompt file (without .md extension)
    
    Returns:
        The prompt text, or None if the file doesn't exist or can't be read
    
    Example:
        >>> system_prompt = load_prompt("system_prompt")
        >>> if system_prompt:
        ...     print(system_prompt)
    """
    prompt_path = _PROMPTS_DIR / f"{prompt_name}.md"
    
    try:
        return prompt_path.read_text(encoding="utf-8")
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
        >>> prompt = format_prompt("system_prompt", 
        ...                        company_name="Example Corp",
        ...                        domains_text="Technology")
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
