"""
OpenAI-based company research adjuster.

Adjusts CV data based on target company research using OpenAI.
"""

from __future__ import annotations

import os
import json
import logging
from typing import Any, Dict, Optional
from pathlib import Path

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

from .base import CVAdjuster
from ..ml_adjustment.adjuster import MLAdjuster, _research_company_profile
from ..ml_adjustment.prompt_loader import load_prompt, format_prompt
from ..verifiers import get_verifier

LOG = logging.getLogger("cvextract")


class OpenAICompanyResearchAdjuster(CVAdjuster):
    """
    Adjuster that uses OpenAI to tailor CV based on company research.
    
    This adjuster researches a target company and adjusts the CV to highlight
    relevant experience, skills, and technologies. It follows the clean adjuster
    pattern:
    1. Fetch company research
    2. Build system prompt
    3. Call MLAdjuster service
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
        self._ml_adjuster = MLAdjuster(model=self._model, api_key=self._api_key)
    
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
        
        # Step 5: Call MLAdjuster service with payload context
        adjusted = self._ml_adjuster.adjust(
            cv_data, 
            system_prompt, 
            user_context={
                "customer_url": customer_url,
                "user_payload": json.dumps(user_payload),
            }
        )
        
        if adjusted is None:
            LOG.warning("Company research adjust: API call failed; using original CV.")
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

