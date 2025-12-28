"""
CLI execution step: Adjust JSON data for customer.

Handles the AI-powered adjustment phase where CV data is tailored
for a specific customer using OpenAI.
"""

from __future__ import annotations

import json
import traceback
from pathlib import Path

from .cli_config import UserConfig
from .logging_utils import LOG
from .ml_adjustment import adjust_for_customer, _url_to_cache_filename


def process_adjustment(
    input_file: Path,
    out_json: Path,
    documents_dir: Path,
    research_dir: Path,
    rel_parent: Path,
    config: UserConfig,
) -> Path:
    """
    Adjust JSON data for a specific customer using OpenAI.
    
    Args:
        input_file: Original input file
        out_json: Path to JSON file to adjust
        documents_dir: Base documents directory
        research_dir: Base research directory
        rel_parent: Relative parent directory
        config: User configuration
    
    Returns:
        Path to the JSON file to use for rendering (adjusted or original)
    """
    # If no adjustment needed, return original
    if not config.mode.needs_adjustment or not config.adjust_url:
        return out_json
    
    try:
        # Load original JSON
        with out_json.open("r", encoding="utf-8") as f:
            original = json.load(f)
        
        # Create research cache directory
        research_cache_dir = research_dir / rel_parent
        research_cache_dir.mkdir(parents=True, exist_ok=True)
        research_cache = research_cache_dir / _url_to_cache_filename(config.adjust_url)
        
        # Call OpenAI to adjust the data
        adjusted = adjust_for_customer(
            original, 
            config.adjust_url, 
            model=config.openai_model, 
            cache_path=research_cache
        )
        
        # Determine where to save adjusted JSON
        if config.mode.needs_extraction:
            adjusted_json = out_json.with_name(out_json.stem + ".adjusted.json")
        else:
            # For apply modes, save in documents dir
            out_docx_dir = documents_dir / rel_parent
            out_docx_dir.mkdir(parents=True, exist_ok=True)
            adjusted_json = out_docx_dir / (input_file.stem + ".adjusted.json")
        
        # Save adjusted JSON
        adjusted_json.parent.mkdir(parents=True, exist_ok=True)
        with adjusted_json.open("w", encoding="utf-8") as wf:
            json.dump(adjusted, wf, ensure_ascii=False, indent=2)
        
        return adjusted_json
        
    except Exception as e:
        # If adjustment fails, fall back to original JSON
        if config.debug:
            LOG.error("Adjustment failed: %s", traceback.format_exc())
        return out_json
