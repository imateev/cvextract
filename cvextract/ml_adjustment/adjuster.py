"""
ML-based CV adjustment using OpenAI.

Given extracted JSON data and a customer URL, research the company and adjust
the CV to highlight customer-relevant aspects (e.g., reordering bullets, 
emphasizing tools). The adjusted CV is validated against the CV schema before
being returned to ensure data integrity.

Notes:
- Requires OPENAI_API_KEY in the environment.
- Optional OPENAI_MODEL env var to override default model.
- Adjusted CV data is validated against cv_schema.json.
- Fails gracefully (returns original data) if API/HTTP errors or validation fails.
"""
from __future__ import annotations

import os
import json
import hashlib
import re
from typing import Any, Dict, Optional
from pathlib import Path

import logging

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore

try:
    # OpenAI >= 1.0 style client
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

from .prompt_loader import format_prompt, load_prompt
from ..verifiers import get_verifier

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
    ML-based CV adjuster using OpenAI.
    
    This class provides a clean interface for adjusting CV data based on
    a target company's profile and technology interests.
    """
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        """
        Initialize the ML adjuster.
        
        Args:
            model: OpenAI model to use (default: "gpt-4o-mini")
            api_key: Optional OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
    
    def adjust(
        self, 
        cv_data: Dict[str, Any], 
        target_url: str,
        cache_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """
        Adjust CV data using ML based on target URL.
        
        Args:
            cv_data: The extracted CV data
            target_url: URL to the target customer's website
            cache_path: Optional path to cache research results
        
        Returns:
            Adjusted CV data dict, or original data if adjustment fails
        """
        if not self.api_key or OpenAI is None:
            LOG.warning("Customer adjust skipped: OpenAI unavailable or API key missing.")
            return cv_data

        # Step 1: Research company profile
        research_data = _research_company_profile(
            target_url, 
            self.api_key, 
            self.model, 
            cache_path
        )
        
        # If research fails, skip adjustment entirely
        if not research_data:
            LOG.warning("Customer adjust skipped: company research failed")
            return cv_data

        # Step 2: Build system prompt from research data
        system_prompt = _build_system_prompt(research_data)
        
        if not system_prompt:
            LOG.warning("Customer adjust skipped: failed to build system prompt")
            return cv_data

        # Step 3: Call OpenAI to adjust the CV
        client = OpenAI(api_key=self.api_key)

        user_payload = {
            "customer_url": target_url,
            "company_profile": research_data,
            "original_json": cv_data,
            "adjusted_json": "",
        }

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
                LOG.warning("Customer adjust: empty completion; using original JSON.")
                return cv_data
            
            # Try to parse JSON; if parsing fails, keep original
            try:
                adjusted = json.loads(content)
                if adjusted is None or not isinstance(adjusted, dict):
                    LOG.warning("Customer adjust: completion is not a dict; using original JSON.")
                    return cv_data
                
                # Validate adjusted CV against schema
                try:
                    schema_verifier = get_verifier("cv-schema-verifier")
                    result = schema_verifier.verify(adjusted)
                    if result.ok:
                        LOG.info("The CV was adjusted to better fit the target customer.")
                        return adjusted
                    else:
                        LOG.warning("Customer adjust: adjusted CV failed schema validation (%d errors); using original JSON.", len(result.errors))
                        return cv_data
                except Exception as e:
                    LOG.warning("Customer adjust: schema validation error (%s); using original JSON.", type(e).__name__)
                    return cv_data
            except Exception:
                LOG.warning("Customer adjust: invalid JSON response; using original JSON.")
                return cv_data
        except Exception as e:
            LOG.warning("Customer adjust error (%s); using original JSON.", type(e).__name__)
            return cv_data


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
    Use OpenAI to adjust extracted JSON for a specific customer.
    Returns a new dict; on any error, returns the original data unchanged.
    
    Args:
        data: The extracted CV data
        customer_url: URL to the customer's website
        api_key: Optional OpenAI API key (defaults to OPENAI_API_KEY env var)
        model: Optional OpenAI model (defaults to OPENAI_MODEL env var or 'gpt-4o-mini')
        cache_path: Optional path to cache research results (e.g., <cv_name>.research.json)
    
    Returns:
        Adjusted CV data dict, or original data if adjustment fails
    """
    model = model or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
    adjuster = MLAdjuster(model=model, api_key=api_key)
    return adjuster.adjust(data, customer_url, cache_path=cache_path)
