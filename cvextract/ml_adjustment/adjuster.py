"""
Pure service layer for OpenAI API communication.

This module provides a clean, focused service for communicating with OpenAI's
chat completion API. It handles:
- Client initialization and retry logic
- API calls with appropriate error handling  
- Response parsing

Note: This is a PURE SERVICE LAYER - it does NOT handle:
- Prompt loading (caller provides system_prompt)
- Data validation (caller validates results)
- Business logic or orchestration (caller handles this)

Adjusters using this service should:
1. Load their own prompts
2. Call adjust() or call_openai() with pre-built system_prompt
3. Validate the result themselves
4. Handle failures and return original data
"""
from __future__ import annotations

import os
import json
import re
import hashlib
from typing import Any, Dict, Optional
from pathlib import Path

import logging

from .prompt_loader import format_prompt
from ..verifiers import get_verifier

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

LOG = logging.getLogger("cvextract")


def _url_to_cache_filename(url: str) -> str:
    """
    DEPRECATED: Use openai_company_research_adjuster._url_to_cache_filename instead.
    
    This function is kept for backward compatibility only.
    """
    from ..adjusters.openai_company_research_adjuster import _url_to_cache_filename as real_func
    return real_func(url)


# Load research schema - DEPRECATED
_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "research_schema.json"
_RESEARCH_SCHEMA: Optional[Dict[str, Any]] = None


def _load_research_schema() -> Optional[Dict[str, Any]]:
    """
    DEPRECATED: Use openai_company_research_adjuster._load_research_schema instead.
    
    This function is kept for backward compatibility only.
    """
    from ..adjusters.openai_company_research_adjuster import _load_research_schema as real_func
    return real_func()


def _fetch_customer_page(url: str) -> str:
    """
    DEPRECATED: Use openai_company_research_adjuster._fetch_customer_page instead.
    
    This function is kept for backward compatibility only.
    """
    from ..adjusters.openai_company_research_adjuster import _fetch_customer_page as real_func
    return real_func(url)


def _validate_research_data(data: Any) -> bool:
    """
    DEPRECATED: Use openai_company_research_adjuster._validate_research_data instead.
    
    This function is kept for backward compatibility only.
    """
    from ..adjusters.openai_company_research_adjuster import _validate_research_data as real_func
    return real_func(data)


def _research_company_profile(
    customer_url: str, 
    api_key: str, 
    model: str, 
    cache_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    DEPRECATED: Use openai_company_research_adjuster._research_company_profile instead.
    
    This function is kept for backward compatibility only.
    """
    from ..adjusters.openai_company_research_adjuster import _research_company_profile as real_func
    return real_func(customer_url, api_key, model, cache_path)

