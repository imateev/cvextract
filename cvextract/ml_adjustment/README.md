# ML Adjustment

This module provides a pluggable architecture for ML-based adjustment of CV data to highlight aspects relevant to a target customer.

## Overview

The ML adjustment architecture allows for:

- Automated company research using publicly available information
- CV content optimization based on target customer's technology interests and business domains
- Clean separation of prompts from business logic
- Easy prompt customization through Markdown files
- Caching of company research to avoid redundant API calls

## Core Concepts

### MLAdjuster Interface

The `MLAdjuster` class provides the main interface for adjusting CV data:

```python
from cvextract.ml_adjustment import MLAdjuster
from pathlib import Path

# Create an adjuster instance
adjuster = MLAdjuster(model="gpt-4o-mini")

# Adjust CV data for a target customer
cv_data = {
    "identity": {...},
    "sidebar": {...},
    "overview": "...",
    "experiences": [...]
}

adjusted_data = adjuster.adjust(
    cv_data=cv_data,
    target_url="https://example.com",
    cache_path=Path("example.com.research.json")  # Optional caching
)
```

### Legacy Function

For backward compatibility, the module also exports the `adjust_for_customer` function:

```python
from cvextract.ml_adjustment import adjust_for_customer
from pathlib import Path

adjusted_data = adjust_for_customer(
    data=cv_data,
    customer_url="https://example.com",
    api_key="your-api-key",  # Optional, defaults to OPENAI_API_KEY env var
    model="gpt-4o-mini",      # Optional, defaults to OPENAI_MODEL env var
    cache_path=Path("cache/example.com.research.json")
)
```

## How It Works

The ML adjustment process consists of two main steps:

### 1. Company Research

The adjuster first researches the target company using OpenAI:

- Analyzes the company website URL
- Gathers publicly available information
- Extracts:
  - Company name and description
  - Business domains (industries, sectors)
  - Technology signals (relevant technologies and their importance)
  - Acquisition history
  - Rebranding information
  - Owned and used products

Research results are cached to avoid redundant API calls for the same company.

### 2. CV Adjustment

Based on the company research, the adjuster:

- Reorders bullets to highlight relevant experience
- Emphasizes technologies that match the customer's interests
- Adjusts descriptions to better align with the customer's domain
- Makes explicit connections between CV content and customer's products/ecosystem
- Maintains factual accuracy (no invention of experience or skills)

## Prompts

Prompts are stored as Markdown files in the `prompts/` subdirectory for easy editing and version control:

- `system_prompt.md`: Main instructions for CV adjustment
- `website_analysis_prompt.md`: Instructions for company research

### Customizing Prompts

You can customize prompts by editing the Markdown files directly. The `prompt_loader` utility handles loading and formatting:

```python
from cvextract.ml_adjustment.prompt_loader import load_prompt, format_prompt

# Load a prompt template
template = load_prompt("system_prompt")

# Load and format with variables
formatted = format_prompt(
    "website_analysis_prompt",
    customer_url="https://example.com",
    schema=json.dumps(schema)
)
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Required for OpenAI API access
- `OPENAI_MODEL`: Optional, defaults to "gpt-4o-mini"

### Cache Files

Research results are cached as JSON files using a deterministic filename based on the URL:

```python
from cvextract.ml_adjustment import _url_to_cache_filename

cache_name = _url_to_cache_filename("https://www.example.com/about")
# Returns: "example.com-abc12345.research.json"
```

## Examples

### Basic Usage

```python
from cvextract.ml_adjustment import MLAdjuster
import json
from pathlib import Path

# Load CV data
with open("cv.json", "r") as f:
    cv_data = json.load(f)

# Create adjuster
adjuster = MLAdjuster(model="gpt-4o-mini")

# Adjust for target customer
adjusted = adjuster.adjust(
    cv_data=cv_data,
    target_url="https://example.com"
)

# Save adjusted data
with open("cv_adjusted.json", "w") as f:
    json.dump(adjusted, f, indent=2)
```

### With Caching

```python
from cvextract.ml_adjustment import MLAdjuster
from pathlib import Path

adjuster = MLAdjuster()

# First call: performs research and caches result
adjusted1 = adjuster.adjust(
    cv_data=cv_data,
    target_url="https://example.com",
    cache_path=Path("cache/example.research.json")
)

# Second call: uses cached research (faster, no API call)
adjusted2 = adjuster.adjust(
    cv_data=cv_data2,
    target_url="https://example.com",
    cache_path=Path("cache/example.research.json")
)
```

### Using Different Models

```python
from cvextract.ml_adjustment import MLAdjuster

# Use GPT-4 for higher quality
adjuster_gpt4 = MLAdjuster(model="gpt-4", api_key="your-key")
adjusted = adjuster_gpt4.adjust(cv_data, "https://example.com")

# Use GPT-3.5 for lower cost
adjuster_gpt35 = MLAdjuster(model="gpt-3.5-turbo")
adjusted = adjuster_gpt35.adjust(cv_data, "https://example.com")
```

### Error Handling

The adjuster fails gracefully and returns the original data on any error:

```python
from cvextract.ml_adjustment import MLAdjuster
import logging

# Enable logging to see warnings
logging.basicConfig(level=logging.INFO)

adjuster = MLAdjuster(api_key="invalid-key")
result = adjuster.adjust(cv_data, "https://example.com")

# result == cv_data (original, unadjusted)
# Logs: "Customer adjust skipped: OpenAI unavailable or API key missing."
```

## Integration with Existing Pipeline

The ML adjustment module integrates seamlessly with the existing pipeline through the `pipeline.py` module, which imports and uses the adjustment functionality:

```python
from cvextract.ml_adjustment import adjust_for_customer, _url_to_cache_filename

# In extract-apply or apply modes
if adjust_url:
    research_cache = research_dir / _url_to_cache_filename(adjust_url)
    adjusted = adjust_for_customer(
        original, 
        adjust_url, 
        model=openai_model, 
        cache_path=research_cache
    )
```

## Module Organization

All ML adjustment code is organized in the `cvextract/ml_adjustment/` directory:

```
cvextract/ml_adjustment/
├── __init__.py           # Public API exports
├── adjuster.py           # MLAdjuster class and main logic
├── prompt_loader.py      # Utility for loading prompts from files
├── prompts/
│   ├── system_prompt.md              # CV adjustment instructions
│   └── website_analysis_prompt.md    # Company research instructions
└── README.md             # This file
```

The module maintains a clean boundary with minimal public API surface through the `__all__` export in `__init__.py`.

## Requirements

- `openai` package (OpenAI Python client)
- `requests` package (for company page fetching)
- Valid OpenAI API key

## Notes

- The module uses OpenAI's chat completion API (OpenAI >= 1.0)
- Research results are validated for required fields before caching
- All prompts use conservative instructions to avoid hallucination
- Technology alignment follows strict rules to maintain factual accuracy
- Corporate lineage connections are only made when directly verifiable
