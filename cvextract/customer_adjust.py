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

    client = OpenAI(api_key=api_key)

    system_prompt = (
        "You are a helpful assistant that adjusts JSON resumes for a target customer. "
        "Given a JSON representing a CV, return a modified JSON that keeps the same schema and keys, "
        "but reorders bullets, highlights relevant tools/industries, and adjusts descriptions to better match the customer's domain. "
        "Do not invent experience or add new keys. Keep types identical. Return ONLY raw JSON. Put that raw JSON response in the payload under adjusted_json."
    )

    user_payload = {
        "customer_url": customer_url,
        "customer_page_excerpt": page_text[:30000],  # cap content size
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
