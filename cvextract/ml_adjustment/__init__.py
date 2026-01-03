"""
ML-based CV adjustment module.

This module provides ML-based adjustment of CV data to highlight aspects
relevant to a target customer, using OpenAI to research companies and
adjust CV content accordingly.
"""

from .adjuster import _url_to_cache_filename, _research_company_profile

__all__ = [
    "_url_to_cache_filename",
    "_research_company_profile",
]
