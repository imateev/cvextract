"""
Customer-specific adjustment using OpenAI.

Given extracted JSON data and a customer URL, fetch basic info and ask
an LLM to produce an adjusted JSON keeping the same schema while highlighting
customer-relevant aspects (e.g., reordering bullets, emphasizing tools).

Notes:
- Requires OPENAI_API_KEY in the environment.
- Optional OPENAI_MODEL env var to override default model.
- Fails gracefully (returns original data) if API/HTTP errors occur.
"""
from __future__ import annotations

import os
import json
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

LOG = logging.getLogger("cvextract")

# Load research schema
_SCHEMA_PATH = Path(__file__).parent.parent / "research_schema.json"
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
    """Validate that research data has required fields."""
    return isinstance(data, dict) and "name" in data and "domains" in data


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
    
    # Build research prompt
    research_prompt = f"""You are an expert company research and profiling system.

Given the company website URL below, use it as a starting point to gather available public information about the company to fill out the profile. Use your knowledge of publicly available information, business databases, industry trends, and other public sources to research the company.

URL:
{customer_url}

TASK:
Generate a single JSON object that conforms EXACTLY to the following JSON Schema:
- Include only fields defined in the schema
- Do not add extra fields
- Omit fields if information is unavailable
- Use conservative inference and assign confidence values where applicable
- Base your research on publicly available information about the company
- If making inferences, ensure they are supported by observable signals from public sources

OUTPUT RULES:
- Output VALID JSON only
- Do NOT include markdown, comments, or explanations
- Do NOT wrap the JSON in code fences
- Ensure all enums and data types match the schema
- Ensure confidence values are between 0 and 1

SEMANTIC GUIDELINES:
- "domains" should reflect the company's primary business areas (industries, sectors, or problem spaces)
- "technology_signals" should represent inferred or observed technology relevance based on public information
- "interest_level" reflects importance to the business, not maturity
- "signals" should briefly state the evidence for the inference from public sources
- "acquisition_history" should include past acquisitions and ownership changes from public business databases (e.g., Northdata, Crunchbase, etc.)
- "rebranded_from" should list previous company names if the company has been rebranded
- "owned_products" should list concrete products/services the company owns, develops, or sells (not abstract technologies)
- "used_products" should list concrete products, tools, and platforms the company uses in their tech stack or operations (not abstract technologies)

JSON SCHEMA:
{json.dumps(schema, indent=2)}"""
    
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
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    model = model or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"

    if not api_key or OpenAI is None:
        LOG.warning("Customer adjust skipped: OpenAI unavailable or API key missing.")
        return data

    # Step 1: Research company profile
    research_data = _research_company_profile(customer_url, api_key, model, cache_path)
    
    # If research fails, skip adjustment entirely
    if not research_data:
        LOG.warning("Customer adjust skipped: company research failed")
        return data

    client = OpenAI(api_key=api_key)

    # Step 2: Build enhanced system prompt using structured research data
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
    
    system_prompt = f"""You are a helpful assistant that adjusts JSON resumes for a target customer.

CUSTOMER PROFILE:
Company: {company_name}
Description: {company_desc}
Business Domains: {domains_text}{tech_signals_text}

TASK:
Given a JSON representing a CV, return a modified JSON that keeps the same schema and keys, 
but reorders bullets, highlights relevant tools/industries, and adjusts descriptions to better 
match the customer's domain and technology interests.

RULES:
- Do not invent experience or add new keys
- Keep types identical
- Prioritize experience and skills relevant to the customer's domains and technology signals
- Emphasize technologies with high interest_level
- Return ONLY raw JSON
- Put that raw JSON response in the payload under adjusted_json"""

    user_payload = {
        "customer_url": customer_url,
        "company_profile": research_data,
        "original_json": data,
        "adjusted_json": "",
    }

    try:
        # Use responses in JSON mode when available
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_payload)},
            ],
            temperature=0.2,
        )
        content = completion.choices[0].message.content if completion.choices else None
        if not content:
            LOG.warning("Customer adjust: empty completion; using original JSON.")
            return data
        # Try to parse JSON; if parsing fails, keep original
        try:
            adjusted = json.loads(content)
            if isinstance(adjusted, dict):
                LOG.info("The CV was adjusted to better fit the target customer.")
                return adjusted["adjusted_json"]
            LOG.warning("Customer adjust: completion is not a dict; using original JSON.")
            return data
        except Exception:
            LOG.warning("Customer adjust: invalid JSON response; using original JSON.")
            return data
    except Exception as e:
        LOG.warning("Customer adjust error (%s); using original JSON.", type(e).__name__)
        return data
