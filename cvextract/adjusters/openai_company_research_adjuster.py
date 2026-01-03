"""
OpenAI-based company research adjuster.

Adjusts CV data based on target company research using OpenAI.
"""

from __future__ import annotations

import os
import json
import logging
import hashlib
import re
from typing import Any, Dict, Optional
from pathlib import Path

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

try:
    import requests
except Exception:  # pragma: no cover
    requests = None  # type: ignore

from .base import CVAdjuster
from ..ml_adjustment.prompt_loader import load_prompt, format_prompt
from ..verifiers import get_verifier

LOG = logging.getLogger("cvextract")


# Research schema cache
_SCHEMA_PATH = Path(__file__).parent.parent / "contracts" / "research_schema.json"
_RESEARCH_SCHEMA: Optional[Dict[str, Any]] = None


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
    """Fetch the content of a URL."""
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


class OpenAICompanyResearchAdjuster(CVAdjuster):
    """
    Adjuster that uses OpenAI to tailor CV based on company research.
    
    This adjuster researches a target company and adjusts the CV to highlight
    relevant experience, skills, and technologies. It follows the clean adjuster
    pattern:
    1. Fetch company research
    2. Build system prompt
    3. Call OpenAI API directly
    4. Validate result with schema verifier
    5. Return adjusted CV or original on failure
    """
    
    def __init__(self, model: str = "gpt-4o-mini", api_key: Optional[str] = None):
        """
        Initialize the adjuster.
        
        Args:
            model: OpenAI model to use (default: "gpt-4o-mini")
            api_key: Optional OpenAI API key (defaults to OPENAI_API_KEY env var)
        """
        self._model = model
        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
    
    def name(self) -> str:
        """Return adjuster name."""
        return "openai-company-research"
    
    def description(self) -> str:
        """Return adjuster description."""
        return "Adjusts CV based on target company research using OpenAI"
    
    def validate_params(self, **kwargs) -> None:
        """
        Validate required parameters.
        
        Args:
            **kwargs: Must contain 'customer_url' or 'customer-url' (with or without hyphen)
        
        Raises:
            ValueError: If customer_url is missing
        """
        # Normalize parameter names (CLI uses hyphens, Python uses underscores)
        has_customer_url = 'customer_url' in kwargs or 'customer-url' in kwargs
        
        if not has_customer_url or not (kwargs.get('customer_url') or kwargs.get('customer-url')):
            raise ValueError(f"Adjuster '{self.name()}' requires 'customer-url' parameter")
    
    def adjust(self, cv_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Adjust CV based on company research.
        
        Args:
            cv_data: The CV data to adjust
            **kwargs: Must contain 'customer_url' (or 'customer-url'), optional 'cache_path'
        
        Returns:
            Adjusted CV data, or original data if adjustment fails
        """
        self.validate_params(**kwargs)
        
        if not self._api_key or OpenAI is None:
            LOG.warning("Company research adjust skipped: OpenAI unavailable or API key missing.")
            return cv_data
        
        # Normalize parameter names (CLI uses hyphens, Python uses underscores)
        customer_url = kwargs.get('customer_url', kwargs.get('customer-url'))
        cache_path = kwargs.get('cache_path')
        
        # Step 1: Research company profile
        LOG.info("Researching company at %s", customer_url)
        research_data = _research_company_profile(
            customer_url, 
            self._api_key, 
            self._model, 
            cache_path
        )
        
        if not research_data:
            LOG.warning("Company research adjust: failed to research company; using original CV.")
            return cv_data
        
        # Step 2: Build research context text
        # Extract key information from research data for the system prompt
        domains_text = ", ".join(research_data.get("domains", []))
        company_name = research_data.get("name", "the company")
        company_desc = research_data.get("description", "")
        
        # Build technology signals context
        tech_signals_parts = []
        if research_data.get("technology_signals"):
            tech_signals_parts.append("Key Technology Signals:")
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
        
        # Build the research context
        research_context = f"Company: {company_name}\n"
        if company_desc:
            research_context += f"Description: {company_desc}\n"
        if domains_text:
            research_context += f"Domains: {domains_text}\n"
        if tech_signals_text:
            research_context += f"{tech_signals_text}"
        
        # Step 3: Load system prompt template with research context
        system_prompt = format_prompt("adjuster_promp_for_a_company", research_context=research_context)
        
        if not system_prompt:
            LOG.warning("Company research adjust: failed to load prompt template; using original CV.")
            return cv_data
        
        # Step 4: Create user payload with research data and cv_data
        user_payload = {
            "company_research": research_data,
            "original_json": cv_data,
            "adjusted_json": "",
        }
        
        # Step 5: Call OpenAI API directly
        try:
            client = OpenAI(api_key=self._api_key)
            completion = client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_payload)},
                ],
                temperature=0.2,
            )
            
            adjusted_json_str = completion.choices[0].message.content
            adjusted = json.loads(adjusted_json_str)
        except (json.JSONDecodeError, ValueError, KeyError, IndexError, AttributeError) as e:
            LOG.warning("Company research adjust: failed to parse response (%s); using original CV.", type(e).__name__)
            return cv_data
        except Exception as e:
            LOG.warning("Company research adjust: API call failed (%s); using original CV.", type(e).__name__)
            return cv_data
        
        if adjusted is None:
            LOG.warning("Company research adjust: API call returned null; using original CV.")
            return cv_data
        
        # Step 6: Validate adjusted CV against schema
        if not isinstance(adjusted, dict):
            LOG.warning("Company research adjust: result is not a dict; using original CV.")
            return cv_data
        
        try:
            cv_verifier = get_verifier("cv-schema-verifier")
            validation_result = cv_verifier.verify(adjusted)
            
            if validation_result.ok:
                LOG.info("The CV was adjusted to better fit the target company.")
                return adjusted
            else:
                LOG.warning(
                    "Company research adjust: adjusted CV failed schema validation (%d errors); using original CV.",
                    len(validation_result.errors)
                )
                return cv_data
        except Exception as e:
            LOG.warning("Company research adjust: schema validation error (%s); using original CV.", type(e).__name__)
            return cv_data

