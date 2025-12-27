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
    
    system_prompt = f"""You are a helpful assistant that adjusts JSON resumes for a target customer.

CUSTOMER PROFILE:
Company: {company_name}
Description: {company_desc}
Business Domains: {domains_text}{tech_signals_text}{acquisition_text}{rebrand_text}{owned_products_text}{used_products_text}

TASK:
Given a JSON representing a CV, return a modified JSON that keeps the same schema and keys, 
but reorders bullets, highlights relevant tools/industries, and adjusts descriptions to better 
match the customer's domain and technology interests.

Hard constraints:
- Do NOT add new fields anywhere.
- Do NOT invent experience, employers, titles, dates, projects, tools, metrics, industries, or responsibilities.
- Keep every value type identical (string stays string, array stays array, etc.).
- Prioritize experience and skills relevant to the customer's domains and technology signals
- Emphasize technologies with high interest_level
- You may only:
  (a) reorder existing array elements (e.g., jobs, bullets, skills),
  (b) rewrite existing text using ONLY facts already present in cv_json,
  (c) optionally remove or generalize irrelevant wording inside existing strings (but do not delete required fields or make them empty unless they already are).

---

Technology alignment & normalization rules (IMPORTANT):

The CV may list specific tools or technologies that are:
- subsets of broader categories mentioned by the customer, or
- informal, abbreviated, or partial names of technologies used by the customer.

You MUST make this relationship explicit in rewritten text, without inventing new tools.

Allowed normalization patterns:
- Subset → superset clarification  
  Example:
  - CV: "Git"
  - Customer: "code versioning systems"
  - Rewrite: "Git-based version control" or "Git version control system"

- Product → vendor-qualified product  
  Example:
  - CV: "Word"
  - Customer: "Microsoft Word"
  - Rewrite: "Microsoft Word"

Name equivalence is allowed only when the expanded form is a commonly
accepted full name of the same product (e.g., "Word" → "Microsoft Word"),
not a different product or suite.

- Specific tool → category-aligned phrasing  
  Example:
  - CV: "Docker"
  - Customer: "containerization technologies"
  - Rewrite: "Docker-based containerization"

Rules for normalization:
- ONLY normalize or expand technologies already present in the CV.
- Do NOT introduce a new tool name that does not already appear in cv_json.
- The rewritten phrasing must remain factually equivalent to the original.
- Do NOT over-expand (e.g., do not say “enterprise document management” if only “Word” exists).
- Prefer parenthetical or descriptive clarification where helpful:
  - "Git (distributed version control)"
  - "Microsoft Word (document authoring)"

If a customer technology is broader than the CV:
- Make the CV technology clearly readable as a member of that broader category.
- Do NOT imply experience with other tools in that category.

If a customer technology is more specific than the CV:
- Only align if the CV already implicitly refers to it (e.g., "Word" → "Microsoft Word").
- Otherwise, do not force alignment.

---

Relevance & emphasis rules:
- Prioritize customer_profile.domain and customer_profile.technology_signals.
- Emphasize technologies with higher interest_level by:
  - moving related bullets/skills higher,
  - rewriting bullets to foreground those tools or categories.
- Highlight domain alignment by reframing existing accomplishments in the customer’s context.
- De-emphasize unrelated technologies by moving them lower and rewriting them more generically, not removing them.

---

Reordering guidance:
- Sort bullets within each role from most relevant → least relevant based on:
  1) direct match to high-interest technologies (including normalized matches),
  2) direct match to customer domains/industries,
  3) senior-impact signals (ownership, scale, performance, reliability, security),
  4) recency (if determinable from existing chronology).
- Reorder skills lists to place high-interest and domain-relevant skills first.
- Do NOT change chronological ordering if the CV implies chronology.

---

Text rewrite rules:
- Preserve meaning and truth; paraphrase only using existing facts.
- Keep bullets concise, action-oriented, and outcome-focused.
- Prefer explicit mention of relevant tools already present in the same role or section.
- You may split bullets ONLY if redistributing existing text and the schema already allows it.

---

Corporate lineage & product-relationship alignment (STRICT RULES):

The customer_profile may contain structured company research fields such as:
- acquisition_history
- rebranded_from
- owned_products
- used_products

These fields may imply non-obvious relationships between:
- companies,
- products,
- vendors,
- historical owners,
- rebranded entities.

If the CV references a tool, product, platform, or vendor that has a VERIFIABLE relationship to the customer_profile via these fields, you MUST make that relationship explicit in rewritten text so that a non-expert reader (e.g., HR) can understand the connection.

A relationship is considered VERIFIABLE only if it can be established
by a direct match or explicit reference within a single field or across
two adjacent fields of the customer_profile (e.g., CV item ↔ owned_products,
CV item ↔ acquisition_history.owner).

Do NOT perform multi-hop inference across unrelated fields.

Examples of allowed clarifications:
- Historical ownership:
  - CV: "Worked with software from a third-party vendor"
  - Customer profile:
      acquisition_history indicates shared historical ownership between the vendor and the customer company
  - Rewrite:
    "Worked with software from a vendor that operated within the same corporate group at the time"

- Product ownership:
  - CV: "Experience with XYZ Platform"
  - Customer profile:
      owned_products includes name: "XYZ Platform"
  - Rewrite:
    "Experience with XYZ Platform (owned and developed by <customer company>)"

- Corporate separation or spin-off:
  - Customer profile notes indicate the company was formerly owned by another entity
  - Rewrite may clarify:
    "(at the time part of the Moody’s organization)" or
    "(prior to the company becoming an independent entity)"

---

Hard constraints for relationship inference:
- Do NOT invent relationships.
- Do NOT guess or hallucinate acquisitions, ownership, or product lineage.
- ONLY make relationships explicit if they are directly supported by:
  - acquisition_history
  - rebranded_from
  - owned_products
  - used_products
- If no direct link exists in these fields, DO NOT imply one.

Clarity rules:
- The rewritten text should clarify relationships, not exaggerate them.
- Use neutral, factual phrasing:
  - "part of"
  - "owned by"
  - "formerly owned by"
  - "within the ecosystem of"
- Avoid marketing language or assumptions of depth of experience beyond what the CV states.

Scope limits:
- Do NOT imply experience with the parent company as a whole if the CV only mentions a subsidiary product.
- Do NOT imply experience with multiple products unless they are explicitly listed in the CV.
- Do NOT imply continued usage if the relationship is historical unless timing is explicitly stated.

---

Integration with relevance scoring:
- If a clarified relationship increases relevance to the customer:
  - Move that bullet or skill higher in ordering.
  - Prefer rewritten bullets that surface the relationship early.
- If the relationship is historical or indirect:
  - Keep the clarification concise and parenthetical.
  
  EXTREMELY IMPORTANT:
  - Return ONLY RAW JSON.
  - Do NOT include any explanations, comments, or markdown.
  - Do NOT wrap the JSON in code fences.
  - Ensure the output is valid JSON that can be parsed without errors.
"""

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
            if adjusted is not None:
                LOG.info("The CV was adjusted to better fit the target customer.")
                return adjusted
            LOG.warning("Customer adjust: completion is not a dict; using original JSON.")
            return data
        except Exception:
            LOG.warning("Customer adjust: invalid JSON response; using original JSON.")
            return data
    except Exception as e:
        LOG.warning("Customer adjust error (%s); using original JSON.", type(e).__name__)
        return data
