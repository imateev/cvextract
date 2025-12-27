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
import re
from typing import Any, Dict, Optional

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

try:
    from html.parser import HTMLParser
except Exception:  # pragma: no cover
    HTMLParser = None  # type: ignore

LOG = logging.getLogger("cvextract")


# Industry keywords for inference - module-level constant
_INDUSTRY_KEYWORDS = {
    "technology": ["software", "tech", "cloud", "ai", "machine learning", "data"],
    "finance": ["financial", "banking", "investment", "fintech"],
    "healthcare": ["health", "medical", "pharmaceutical", "biotech"],
    "retail": ["retail", "ecommerce", "e-commerce", "shopping"],
    "consulting": ["consulting", "advisory", "professional services"],
    "education": ["education", "learning", "training"],
}


class _MetaParser(HTMLParser):
    """Simple HTML parser to extract meta tags and basic content."""
    
    def __init__(self):
        super().__init__()
        self.meta_data = {}
        self.title = ""
        self.in_title = False
        
    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "meta":
            # Extract common meta tags
            name = attrs_dict.get("name", "").lower()
            property_val = attrs_dict.get("property", "").lower()
            content = attrs_dict.get("content", "")
            
            if name in ("description", "keywords", "author"):
                self.meta_data[name] = content
            elif property_val in ("og:description", "og:title", "og:site_name"):
                key = property_val.replace("og:", "og_")
                self.meta_data[key] = content
        elif tag == "title":
            self.in_title = True
            
    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
            
    def handle_data(self, data):
        if self.in_title and data.strip():
            # Concatenate title parts in case there are multiple text nodes
            if self.title:
                self.title += " " + data.strip()
            else:
                self.title = data.strip()


def _research_company_url(url: str) -> Dict[str, Any]:
    """
    Research a company URL to extract structured metadata.
    
    Attempts to extract:
    - industry: inferred from description/keywords
    - mission: extracted from meta description or og:description
    - focus: extracted from keywords or page title
    
    Returns a dict with available metadata. On any error, returns an empty dict.
    """
    if not requests or not HTMLParser:
        LOG.debug("URL research skipped: requests or HTMLParser unavailable.")
        return {}
    
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            LOG.debug("URL research failed: HTTP %d", resp.status_code)
            return {}
        
        html_content = resp.text or ""
        if not html_content:
            return {}
        
        # Parse HTML to extract meta information
        parser = _MetaParser()
        try:
            parser.feed(html_content)
        except Exception:
            # HTML parsing can fail on malformed HTML
            pass
        
        # Build structured metadata
        research_data = {}
        
        # Extract mission from description
        mission = (
            parser.meta_data.get("og_description") or 
            parser.meta_data.get("description") or
            ""
        )
        if mission:
            research_data["mission"] = mission[:500]  # cap length
        
        # Extract focus from title or keywords
        focus_parts = []
        if parser.title:
            focus_parts.append(parser.title)
        if parser.meta_data.get("keywords"):
            focus_parts.append(parser.meta_data["keywords"])
        
        if focus_parts:
            research_data["focus"] = " | ".join(focus_parts)[:500]
        
        # Try to infer industry from keywords or description
        keywords = parser.meta_data.get("keywords", "").lower()
        description = parser.meta_data.get("description", "").lower()
        combined = f"{keywords} {description}"
        
        # Industry inference using word boundary matching to avoid false positives
        detected_industries = []
        for industry, terms in _INDUSTRY_KEYWORDS.items():
            for term in terms:
                # Use word boundary matching to avoid false positives like "unfinancial"
                if re.search(r'\b' + re.escape(term) + r'\b', combined):
                    detected_industries.append(industry)
                    break  # Only add industry once
        
        if detected_industries:
            research_data["industry"] = ", ".join(detected_industries[:3])  # limit to top 3
        
        if research_data:
            LOG.debug("URL research extracted: %s", list(research_data.keys()))
        
        return research_data
        
    except Exception as e:
        LOG.debug("URL research error (%s); returning empty data.", type(e).__name__)
        return {}


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


def adjust_for_customer(data: Dict[str, Any], customer_url: str, *, api_key: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Use OpenAI to adjust extracted JSON for a specific customer.
    Returns a new dict; on any error, returns the original data unchanged.
    """
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    model = model or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"

    if not api_key or OpenAI is None:
        LOG.warning("Customer adjust skipped: OpenAI unavailable or API key missing.")
        return data

    # Fetch page content to enrich the prompt
    page_text = _fetch_customer_page(customer_url)
    
    # Research company URL for structured metadata
    research_data = _research_company_url(customer_url)

    client = OpenAI(api_key=api_key)

    system_prompt = (
        "You are a helpful assistant that adjusts JSON resumes for a target customer. "
        "Given a JSON representing a CV, return a modified JSON that keeps the same schema and keys, "
        "but reorders bullets, highlights relevant tools/industries, and adjusts descriptions to better match the customer's domain. "
        "Use the provided company research data (industry, mission, focus) to better tailor the adjustments. "
        "Do not invent experience or add new keys. Keep types identical. Return ONLY raw JSON. Put that raw JSON response in the payload under adjusted_json."
    )

    user_payload = {
        "customer_url": customer_url,
        "customer_page_excerpt": page_text[:30000],  # cap content size
        "company_research": research_data,  # structured metadata
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
