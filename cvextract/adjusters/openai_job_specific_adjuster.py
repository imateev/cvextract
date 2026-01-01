"""
OpenAI-based job-specific adjuster.

Adjusts CV data based on a specific job description using OpenAI.
"""

from __future__ import annotations

import os
import json
import logging
from pathlib import Path
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

LOG = logging.getLogger("cvextract")


def _fetch_job_description(url: str) -> str:
    """Fetch job description from URL."""
    if not requests:
        return ""
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            return ""
        return resp.text or ""
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
            **kwargs: Must contain either 'job_url' or 'job_description'
        
        Raises:
            ValueError: If neither job_url nor job_description is provided
        """
        if 'job_url' not in kwargs and 'job_description' not in kwargs:
            raise ValueError(
                f"Adjuster '{self.name()}' requires either 'job_url' or 'job_description' parameter"
            )
    
    def adjust(self, cv_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Adjust CV based on job description.
        
        Args:
            cv_data: The CV data to adjust
            **kwargs: Must contain either 'job_url' or 'job_description'
        
        Returns:
            Adjusted CV data, or original data if adjustment fails
        """
        self.validate_params(**kwargs)
        
        if not self._api_key or OpenAI is None:
            LOG.warning("Job-specific adjust skipped: OpenAI unavailable or API key missing.")
            return cv_data
        
        # Get job description from URL or direct text
        job_description = kwargs.get('job_description', '')
        if not job_description and 'job_url' in kwargs:
            job_url = kwargs['job_url']
            LOG.info("Fetching job description from %s", job_url)
            job_description = _fetch_job_description(job_url)
            if not job_description:
                LOG.warning("Job-specific adjust: failed to fetch job description from URL")
                return cv_data
        
        # Build prompt using template
        system_prompt = format_prompt("job_specific_prompt", job_description=job_description)
        
        if not system_prompt:
            LOG.warning("Job-specific adjust skipped: failed to load prompt template")
            return cv_data
        
        # Call OpenAI to adjust the CV
        try:
            client = OpenAI(api_key=self._api_key)
            
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
                    LOG.info("The CV was adjusted to better fit the job description.")
                    return adjusted
                LOG.warning("Job-specific adjust: completion is not a dict; using original JSON.")
                return cv_data
            except Exception:
                LOG.warning("Job-specific adjust: invalid JSON response; using original JSON.")
                return cv_data
        except Exception as e:
            LOG.warning("Job-specific adjust error (%s); using original JSON.", type(e).__name__)
            return cv_data
