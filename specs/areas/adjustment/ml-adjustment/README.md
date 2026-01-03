# ML Adjustment

## Overview

The ML adjustment feature provides core OpenAI-based CV optimization functionality, enabling automated tailoring of CV content based on target context (company, job, etc.).

## Status

**Active** - Core adjustment infrastructure

## Description

The `MLAdjuster` class provides:
1. Integration with OpenAI API for intelligent content analysis
2. Prompt-based CV restructuring and emphasis
3. Factual accuracy preservation (no invention of experience)
4. Support for multiple OpenAI models
5. Schema validation of adjusted CV data before returning
6. Graceful error handling with fallback to original data

## Entry Points

### Programmatic API

```python
from cvextract.ml_adjustment import MLAdjuster
from pathlib import Path

adjuster = MLAdjuster(model="gpt-4o-mini")
adjusted_cv = adjuster.adjust(
    cv_data=cv_data,
    target_url="https://example.com",
    cache_path=Path("cache/example.research.json")
)
```

### Legacy API

```python
from cvextract.ml_adjustment import adjust_for_customer

adjusted_cv = adjust_for_customer(
    data=cv_data,
    customer_url="https://example.com",
    api_key="sk-proj-...",  # Optional
    model="gpt-4o-mini",     # Optional
    cache_path=Path("cache/example.research.json")
)
```

## Configuration

### Parameters

- `cv_data`: CV dictionary conforming to CV schema
- `target_url`: Company website URL for research
- `cache_path`: Optional path for caching research results
- `model`: OpenAI model name (default: `gpt-4o-mini`)
- `api_key`: OpenAI API key (default: `OPENAI_API_KEY` env var)

### Environment Variables

- **`OPENAI_API_KEY`** (required): OpenAI API key
- **`OPENAI_MODEL`** (optional): Default model name

## Interfaces

### Input

CV JSON data + context parameters (URL, job description, etc.)

### Output

Adjusted CV JSON with:
- Reordered bullet points (relevant items first)
- Emphasized relevant technologies
- Adjusted descriptions for target context
- Same schema structure (no new fields)
- **Validated** against CV schema before returning
- Falls back to original CV if validation fails

## Dependencies

### Internal Dependencies

- `cvextract.ml_adjustment.prompt_loader` - Prompt file
- `cvextract.verifiers.CVSchemaVerifier` - Validates adjusted CV before returning loading
- `cvextract.contracts.research_schema.json` - Research data schema
- `cvextract.contracts.cv_schema.json` - CV data schema

### External Dependencies

- `openai` (>= 1.0) - OpenAI Python client
- `requests` - HTTP client for web scraping

### Integration Points

- Used by `cvextract.adjusters.OpenAICompanyResearchAdjuster`
- Used by `cvextract.adjusters.OpenAIJobSpecificAdjuster`
- Used by `cvextract.pipeline` for adjustment stage

## Test Coverage

Tested in:
- `tests/test_ml_adjustment.py` - Unit tests with mocked OpenAI
- `tests/test_adjusters.py` - Integration tests
- `tests/test_pipeline.py` - End-to-end tests

## Implementation History

The ML adjustment module was created to support automated CV tailoring for customer-specific proposals and job applications.

**Key Files**:
- `cvextract/ml_adjustment/adjuster.py` - Core logic
- `cvextract/ml_adjustment/prompt_loader.py` - Prompt management
- `cvextract/ml_adjustment/prompts/*.md` - Prompt templates

## Open Questions

1. **Model Selection**: Should we support fine-tuned models?
2. **Prompt Versioning**: Should we version prompts separately from code?
3. **Batch Optimization**: Should we batch multiple CVs in one API call?
4. **Quality Metrics**: How do we measure adjustment quality?

## File Paths

- Implementation: `cvextract/ml_adjustment/adjuster.py`
- Prompt Loader: `cvextract/ml_adjustment/prompt_loader.py`
- Prompts: `cvextract/ml_adjustment/prompts/*.md`
- Tests: `tests/test_ml_adjustment.py`
- Documentation: `cvextract/ml_adjustment/README.md`

## Related Documentation

- [Adjustment Architecture](../README.md)
- [Company Research & Caching](../company-research-caching/README.md)
- [Named Adjusters](../named-adjusters/README.md)
- Module README: `cvextract/ml_adjustment/README.md`
