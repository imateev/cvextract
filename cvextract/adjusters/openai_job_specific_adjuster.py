"""
OpenAI-based job-specific adjuster.

Adjusts CV data based on a specific job description using OpenAI.
"""

from __future__ import annotations

import os
import json
import logging
import time
import re
from typing import Any, Dict, Optional

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None  # type: ignore

try:
    from openai import OpenAI  # type: ignore
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore

from .base import CVAdjuster
from ..ml_adjustment.prompt_loader import format_prompt
from ..verifiers import get_verifier

LOG = logging.getLogger("cvextract")


def _fetch_job_description(url: str) -> str:
    """
    Fetch job description from URL and extract/clean text content.
    
    Args:
        url: URL to fetch job description from
    
    Returns:
        Cleaned text content (max 5000 chars), or empty string if fetch fails
    """
    if not requests:
        return ""
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return ""
        
        html = resp.text or ""
        if not html:
            return ""
        
        # Remove script and style elements
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', html)
        
        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)  # Collapse multiple spaces
        text = text.strip()
        
        # Limit to first 5000 characters to avoid token limits
        # (typical job posting is 500-2000 chars, this gives plenty of room)
        return text[:5000] if text else ""
    except Exception:
        return ""


class OpenAIJobSpecificAdjuster(CVAdjuster):
    """
    Adjuster that uses OpenAI to tailor CV based on a specific job description.
    
    This adjuster takes a job URL or description and adjusts the CV to highlight
    relevant experience and skills for that specific position.
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
        return "openai-job-specific"
    
    def description(self) -> str:
        """Return adjuster description."""
        return "Adjusts CV based on a specific job description using OpenAI"
    
    def validate_params(self, **kwargs) -> None:
        """
        Validate required parameters.
        
        Args:
            **kwargs: Must contain either 'job_url' or 'job_description' (or hyphenated variants)
        
        Raises:
            ValueError: If neither job_url nor job_description is provided
        """
        # Normalize parameter names (CLI uses hyphens, Python uses underscores)
        has_job_url = 'job_url' in kwargs or 'job-url' in kwargs
        has_job_desc = 'job_description' in kwargs or 'job-description' in kwargs
        
        if not has_job_url and not has_job_desc:
            raise ValueError(
                f"Adjuster '{self.name()}' requires either 'job-url' or 'job-description' parameter"
            )
    
    def adjust(self, cv_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Adjust CV based on job description.
        
        Args:
            cv_data: The CV data to adjust
            **kwargs: Must contain either 'job_url' or 'job_description' (or hyphenated variants)
        
        Returns:
            Adjusted CV data, or original data if adjustment fails
        """
        self.validate_params(**kwargs)
        
        if not self._api_key or OpenAI is None:
            LOG.warning("Job-specific adjust skipped: OpenAI unavailable or API key missing.")
            return cv_data
        
        # Normalize parameter names (CLI uses hyphens, Python uses underscores)
        job_description = kwargs.get('job_description', kwargs.get('job-description', ''))
        job_url = kwargs.get('job_url', kwargs.get('job-url', ''))
        
        # Get job description from URL or direct text
        if not job_description and job_url:
            LOG.info("Fetching job description from %s", job_url)
            job_description = _fetch_job_description(job_url)
            if not job_description:
                LOG.warning("Job-specific adjust: failed to fetch job description from URL")
                return cv_data
        
        # Build prompt using template
        system_prompt = format_prompt("adjuster_promp_for_specific_job", job_description=job_description)
        
        if not system_prompt:
            LOG.warning("Job-specific adjust skipped: failed to load prompt template")
            return cv_data
        
        # Call OpenAI to adjust the CV with exponential backoff on rate limits
        max_retries = 3
        base_wait = 2.0  # Start with 2 seconds for our custom backoff
        
        # Create OpenAI client once (reuse across retries)
        client = OpenAI(
            api_key=self._api_key,
            max_retries=5,  # SDK's built-in retries (handles initial rate limit gracefully)
        )
        
        for attempt in range(max_retries):
            try:
                user_payload = {
                    "job_description": job_description,
                    "original_json": cv_data,
                    "adjusted_json": "",
                }
                
                completion = client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": json.dumps(user_payload)},
                    ],
                    temperature=0.2,
                )
                
                content = completion.choices[0].message.content if completion.choices else None
                if not content:
                    LOG.warning("Job-specific adjust: empty completion; using original JSON.")
                    return cv_data
                
                # Try to parse JSON; if parsing fails, keep original
                try:
                    adjusted = json.loads(content)
                    if adjusted is not None:
                        # Validate adjusted CV against schema
                        cv_verifier = get_verifier("cv-schema-verifier")
                        validation_result = cv_verifier.verify(adjusted)
                        
                        if validation_result.ok:
                            LOG.info("The CV was adjusted to better fit the job description.")
                            return adjusted
                        else:
                            LOG.warning(
                                "Job-specific adjust: adjusted CV failed schema validation (%d errors); using original JSON.",
                                len(validation_result.errors)
                            )
                            return cv_data
                    LOG.warning("Job-specific adjust: completion is not a dict; using original JSON.")
                    return cv_data
                except Exception:
                    LOG.warning("Job-specific adjust: invalid JSON response; using original JSON.")
                    return cv_data
            
            except Exception as e:
                # Check if it's a rate limit error
                error_name = type(e).__name__
                is_rate_limit = "RateLimit" in error_name or "429" in str(e)
                
                if is_rate_limit and attempt < max_retries - 1:
                    # Calculate exponential backoff: base_wait * 2^attempt
                    wait_time = base_wait * (2 ** attempt)
                    LOG.warning(
                        "Job-specific adjust: rate limited (attempt %d/%d), waiting %.1f seconds before retry",
                        attempt + 1, max_retries, wait_time
                    )
                    time.sleep(wait_time)
                    continue
                
                # Not a rate limit error or final attempt
                LOG.warning("Job-specific adjust error (%s); using original JSON.", error_name)
                return cv_data
