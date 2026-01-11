"""
CV adjustment interfaces and implementations.

This module provides pluggable and interchangeable CV adjusters with a registry system.
"""

from .base import CVAdjuster
from .openai_company_research_adjuster import OpenAICompanyResearchAdjuster
from .openai_job_specific_adjuster import OpenAIJobSpecificAdjuster
from .openai_translate_adjuster import OpenAITranslateAdjuster
from .adjuster_registry import (
    register_adjuster,
    get_adjuster,
    list_adjusters,
)


# Register built-in adjusters
register_adjuster(OpenAICompanyResearchAdjuster)
register_adjuster(OpenAIJobSpecificAdjuster)
register_adjuster(OpenAITranslateAdjuster)


__all__ = [
    "CVAdjuster",
    "OpenAICompanyResearchAdjuster",
    "OpenAIJobSpecificAdjuster",
    "OpenAITranslateAdjuster",
    "register_adjuster",
    "get_adjuster",
    "list_adjusters",
]
