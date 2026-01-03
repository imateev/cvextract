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
    Convert a URL to a safe, deterministic filename for caching.
    
    Uses the domain name from the URL and a hash to ensure uniqueness
    while keeping the filename readable and filesystem-safe.
    
    Args:
        url: The company URL
    
    Returns:
        A safe filename like "example.com-abc123.research.json"
    """
    # Extract domain from URL
    # Remove protocol
    domain = re.sub(r'^https?://', '', url.lower())
    # Remove www. prefix if present
    domain = re.sub(r'^www\.', '', domain)
    # Remove path, query, and fragment
    domain = domain.split('/')[0].split('?')[0].split('#')[0]
    # Remove port if present
    domain = domain.split(':')[0]
    
    # Create a short hash for uniqueness (in case of different URLs for same domain)
    url_hash = hashlib.md5(url.lower().encode()).hexdigest()[:8]
    
    # Create safe filename
    safe_domain = re.sub(r'[^a-z0-9.-]', '_', domain)
    
    return f"{safe_domain}-{url_hash}.research.json"


# Load research schema
_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "research_schema.json"
_RESEARCH_SCHEMA: Optional[Dict[str, Any]] = None


def _load_research_schema() -> Optional[Dict[str, Any]]:
    """Load the research schema from file."""
    global _RESEARCH_SCHEMA
    if _RESEARCH_SCHEMA is not None:
        return _RESEARCH_SCHEMA
    try:
        with open(_SCHEMA_PATH, "r", encoding="utf-8") as f:
            _RESEARCH_SCHEMA = json.load(f)
        return _RESEARCH_SCHEMA
    except Exception as e:
        LOG.warning("Failed to load research schema: %s", e)
        return None


def _fetch_customer_page(url: str) -> str:
    if not requests:
        return ""
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return ""
        return resp.text or ""
    except Exception:
        return ""


def _validate_research_data(data: Any) -> bool:
    """
    Validate that research data conforms to the company profile schema.
    
    Uses the CompanyProfileVerifier to ensure the data structure
    matches the research_schema.json requirements.
    """
    if not isinstance(data, dict):
        return False
    
    try:
        verifier = get_verifier("company-profile-verifier")
        result = verifier.verify(data)
        return result.ok
    except Exception as e:
        LOG.warning("Failed to validate research data with verifier: %s", e)
        return False


def _research_company_profile(
    customer_url: str, 
    api_key: str, 
    model: str, 
    cache_path: Optional[Path] = None
) -> Optional[Dict[str, Any]]:
    """
    Research a company profile from its URL using OpenAI.
    
    Args:
        customer_url: The company website URL
        api_key: OpenAI API key
        model: OpenAI model to use
        cache_path: Optional path to cache file (e.g., <cv_name>.research.json)
    
    Returns:
        Dict containing company profile data, or None if research fails
    """
    # Check cache first
    if cache_path and cache_path.exists():
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cached_data = json.load(f)
            # Basic validation that it's a dict with required fields
            if _validate_research_data(cached_data):
                LOG.info("Using cached company research from %s", cache_path)
                return cached_data
        except Exception as e:
            LOG.warning("Failed to load cached research (%s), will re-research", type(e).__name__)
    
    # No valid cache, perform research
    if not OpenAI:
        LOG.warning("Company research skipped: OpenAI unavailable")
        return None
    
    # Load schema
    schema = _load_research_schema()
    if not schema:
        LOG.warning("Company research skipped: schema not available")
        return None
    
    # Build research prompt using template
    research_prompt = format_prompt(
        "website_analysis_prompt",
        customer_url=customer_url,
        schema=json.dumps(schema, indent=2)
    )
    
    if not research_prompt:
        LOG.warning("Company research skipped: failed to load prompt template")
        return None
    
    try:
        client = OpenAI(api_key=api_key)
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": research_prompt}
            ],
            temperature=0.2,
        )
        content = completion.choices[0].message.content if completion.choices else None
        if not content:
            LOG.warning("Company research: empty completion")
            return None
        
        # Parse JSON response
        try:
            research_data = json.loads(content)
            if not isinstance(research_data, dict):
                LOG.warning("Company research: response is not a dict")
                return None
            
            # Basic validation
            if not _validate_research_data(research_data):
                LOG.warning("Company research: missing required fields")
                return None
            
            # Cache the result
            if cache_path:
                try:
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    with open(cache_path, "w", encoding="utf-8") as f:
                        json.dump(research_data, f, ensure_ascii=False, indent=2)
                    LOG.info("Cached company research to %s", cache_path)
                except Exception as e:
                    LOG.warning("Failed to cache research (%s)", type(e).__name__)
            
            LOG.info("Successfully researched company profile")
            return research_data
            
        except json.JSONDecodeError:
            LOG.warning("Company research: invalid JSON response")
            return None
            
    except Exception as e:
        LOG.warning("Company research error (%s)", type(e).__name__)
        return None


def _build_system_prompt(research_data: Dict[str, Any]) -> Optional[str]:
    """
    Build the system prompt from research data.
    
    Args:
        research_data: Company research data
    
    Returns:
        The formatted system prompt, or None if formatting fails
    """
    # Build technology signals text
    tech_signals_parts = []
    if research_data.get("technology_signals"):
        tech_signals_parts.append("\n\nKey Technology Signals:")
        for signal in research_data["technology_signals"]:
            tech = signal.get("technology", "Unknown")
            interest = signal.get("interest_level", "unknown")
            confidence = signal.get("confidence", 0)
            evidence = signal.get("signals", [])
            
            # Format confidence safely
            try:
                conf_str = f"{float(confidence):.2f}"
            except (TypeError, ValueError):
                conf_str = "0.00"
            
            tech_signals_parts.append(f"\n- {tech} (interest: {interest}, confidence: {conf_str})")
            if evidence:
                tech_signals_parts.append(f"\n  Evidence: {'; '.join(evidence[:2])}")
    
    tech_signals_text = "".join(tech_signals_parts)
    domains_text = ", ".join(research_data.get("domains", []))
    company_name = research_data.get("name", "the company")
    company_desc = research_data.get("description", "")
    
    # Build acquisition history text
    acquisition_text = ""
    if research_data.get("acquisition_history"):
        acquisition_text = "\n\nAcquisition History:"
        for acq in research_data["acquisition_history"]:
            owner = acq.get("owner", "Unknown")
            year = acq.get("year", "")
            notes = acq.get("notes", "")
            acquisition_text += f"\n- Owned by {owner}"
            if year:
                acquisition_text += f" ({year})"
            if notes:
                acquisition_text += f": {notes}"
    
    # Build rebranding history text
    rebrand_text = ""
    if research_data.get("rebranded_from"):
        rebrand_text = f"\n\nPrevious Names: {', '.join(research_data['rebranded_from'])}"
    
    # Build owned products text
    owned_products_text = ""
    if research_data.get("owned_products"):
        owned_products_text = "\n\nOwned Products/Services:"
        for product in research_data["owned_products"]:
            name = product.get("name", "Unknown")
            category = product.get("category", "")
            description = product.get("description", "")
            owned_products_text += f"\n- {name}"
            if category:
                owned_products_text += f" ({category})"
            if description:
                owned_products_text += f": {description}"
    
    # Build used products text
    used_products_text = ""
    if research_data.get("used_products"):
        used_products_text = "\n\nProducts/Tools Used by Company:"
        for product in research_data["used_products"]:
            name = product.get("name", "Unknown")
            category = product.get("category", "")
            purpose = product.get("purpose", "")
            used_products_text += f"\n- {name}"
            if category:
                used_products_text += f" ({category})"
            if purpose:
                used_products_text += f": {purpose}"
    
    # Build related companies text
    related_companies_text = ""
    if research_data.get("related_companies"):
        related_companies_text = "\n\nRelated Companies & Partnerships:"
        for company in research_data["related_companies"]:
            name = company.get("name", "Unknown")
            relationship = company.get("relationship_type", "")
            description = company.get("description", "")
            related_companies_text += f"\n- {name}"
            if relationship:
                related_companies_text += f" ({relationship})"
            if description:
                related_companies_text += f": {description}"
    
    # Format the system prompt template
    return format_prompt(
        "system_prompt",
        company_name=company_name,
        company_desc=company_desc,
        domains_text=domains_text,
        tech_signals_text=tech_signals_text,
        acquisition_text=acquisition_text,
        rebrand_text=rebrand_text,
        owned_products_text=owned_products_text,
        used_products_text=used_products_text,
        related_companies_text=related_companies_text
    )


class MLAdjuster:
    """
    Pure service for OpenAI API communication.
    
    This class is a focused service layer for calling OpenAI's chat completion
    API. It is NOT responsible for:
    - Loading or building prompts (caller provides system_prompt)
    - Validating results (caller must validate)
    - Business logic or orchestration (caller handles this)
    
    Usage:
        adjuster = MLAdjuster(api_key="...")
        response = adjuster.adjust(cv_data, system_prompt)
        # Caller now owns: validation, error handling, retry logic
    """
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        """
        Initialize the OpenAI service.
        
        Args:
            model: OpenAI model to use (default: "gpt-4o-mini")
            api_key: Optional OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
    
    def adjust(
        self, 
        cv_data: Dict[str, Any], 
        system_prompt: str,
        user_context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Call OpenAI API to adjust CV data using a system prompt.
        
        Args:
            cv_data: The CV data to adjust
            system_prompt: System prompt for the AI (caller provides this)
            user_context: Optional additional context for the user message (e.g., company profile, job description)
        
        Returns:
            OpenAI response parsed as dict, or None if parsing/API fails
            NOTE: Caller must validate the response - this method does NOT validate
        """
        if not self.api_key or OpenAI is None:
            LOG.warning("MLAdjuster: OpenAI unavailable or API key missing.")
            return None

        client = OpenAI(api_key=self.api_key)
        
        # Build user payload
        user_payload = user_context or {}
        user_payload["original_json"] = cv_data
        user_payload["adjusted_json"] = ""

        try:
            completion = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload)},
                ],
                temperature=0.2,
            )
            content = completion.choices[0].message.content if completion.choices else None
            if not content:
                LOG.warning("MLAdjuster: empty completion response.")
                return None
            
            # Parse and return JSON response
            try:
                adjusted = json.loads(content)
                return adjusted
            except Exception as e:
                LOG.warning("MLAdjuster: invalid JSON response (%s).", type(e).__name__)
                return None
        except Exception as e:
            LOG.warning("MLAdjuster: OpenAI API error (%s).", type(e).__name__)
            return None



# Legacy function for backward compatibility
def adjust_for_customer(
    data: Dict[str, Any], 
    customer_url: str, 
    *, 
    api_key: Optional[str] = None, 
    model: Optional[str] = None,
    cache_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    DEPRECATED: Use OpenAICompanyResearchAdjuster instead.
    
    This function is kept for backward compatibility only.
    New code should use OpenAICompanyResearchAdjuster.adjust() instead.
    
    Args:
        data: The extracted CV data
        customer_url: URL to the customer's website
        api_key: Optional OpenAI API key (defaults to OPENAI_API_KEY env var)
        model: Optional OpenAI model (defaults to OPENAI_MODEL env var or 'gpt-4o-mini')
        cache_path: Optional path to cache research results
    
    Returns:
        Adjusted CV data dict, or original data if adjustment fails
    """
    from ..adjusters import get_adjuster
    
    try:
        model = model or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
        adjuster = get_adjuster("openai-company-research", model=model, api_key=api_key)
        return adjuster.adjust(data, customer_url=customer_url, cache_path=cache_path)
    except Exception as e:
        LOG.warning("adjust_for_customer: failed (%s); returning original data.", type(e).__name__)
        return data

