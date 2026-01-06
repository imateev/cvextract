# Company Research Adjuster

## Overview

The OpenAI Company Research Adjuster provides automated CV tailoring based on target company research. It fetches company information, analyzes it using OpenAI, caches the results for reuse, and adjusts CV content to emphasize relevant experience and skills.

## Status

**Active** - Fully implemented and production-ready

## Description

This adjuster implements a complete company research and CV adjustment pipeline:

1. **Company Research**: Fetches and analyzes target company website content
2. **Structured Extraction**: Extracts company profile using OpenAI (name, description, domains, technologies, etc.)
3. **Schema Validation**: Validates research data against `research_schema.json` using `CompanyProfileVerifier`
4. **Caching**: Stores research results as JSON files for reuse
5. **CV Adjustment**: Uses research to tailor CV content (reorder bullets, emphasize technologies, adjust descriptions)
6. **Output Validation**: Validates adjusted CV against `cv_schema.json` before returning

## Entry Points

### Programmatic API

```python
from pathlib import Path
from cvextract.adjusters import OpenAICompanyResearchAdjuster
from cvextract.cli_config import UserConfig, ExtractStage
from cvextract.shared import UnitOfWork

adjuster = OpenAICompanyResearchAdjuster(model="gpt-4o-mini")
work = UnitOfWork(
    config=UserConfig(target_dir=Path("out"), extract=ExtractStage(source=Path("cv.json"))),
    input=Path("cv.json"),
    output=Path("cv.json"),
)
adjusted_cv = adjuster.adjust(
    work,
    customer_url="https://example.com"
)
```

### CLI Usage

```bash
# Basic usage
export OPENAI_API_KEY="sk-proj-..."

python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com \
  --target output/

# Research cached at: output/research_data/example_com-<hash>.research.json
```

```bash
# With custom model
python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com openai-model=gpt-4 \
  --target output/
```

```bash
# Chained with other adjusters
python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com \
  --adjust name=openai-job-specific job-url=https://example.com/careers/123 \
  --render template=template.docx \
  --target output/
```

### Registry Access

```python
from cvextract.adjusters import get_adjuster
from cvextract.cli_config import UserConfig, ExtractStage
from cvextract.shared import UnitOfWork
from pathlib import Path

adjuster = get_adjuster("openai-company-research", model="gpt-4o-mini")
work = UnitOfWork(
    config=UserConfig(target_dir=Path("out"), extract=ExtractStage(source=Path("cv.json"))),
    input=Path("cv.json"),
    output=Path("cv.json"),
)
adjusted_cv = adjuster.adjust(
    work,
    customer_url="https://example.com"
)
```

## Configuration

### CLI Parameters

- `name=openai-company-research`: Adjuster name (required to select this adjuster)
- `customer-url=<url>`: Company website URL (required)
- `openai-model=<model>`: OpenAI model to use (optional, defaults to `gpt-4o-mini`)

### Environment Variables

- **`OPENAI_API_KEY`** (required): OpenAI API key for company research and CV adjustment

### Cache Configuration

Cache paths are automatically determined:
- **Pattern**: `{target}/research_data/{sanitized_url}-{hash}.research.json`
- **Sanitization**: URLs are converted to safe filenames (e.g., `https://www.example.com/about` → `example.com-abc12345.research.json`)

## Interfaces

### Input Parameters

- `cv_data`: CV dictionary conforming to CV schema
- `customer_url`: Company website URL (required)

### Output

Adjusted CV JSON with:
- Reordered bullet points (company-relevant items first)
- Emphasized technologies matching company profile
- Adjusted descriptions for target company context
- Same schema structure (no new fields)
- Validated against CV schema before returning
- Falls back to original CV if validation fails

### Research Data Schema

Defined in `cvextract/contracts/research_schema.json`:

```json
{
  "name": "Company Name",
  "description": "Company description",
  "domains": ["Industry", "Sector"],
  "technology_signals": {
    "Python": 3,
    "AWS": 5
  },
  "acquisition_history": ["Acquired Company A in 2020"],
  "rebranded_from": ["OldCo"],
  "owned_products": ["Product X", "Service Y"],
  "used_products": ["Tool A", "Platform B"]
}
```

## Dependencies

### Internal Dependencies

- `cvextract.adjusters.base.CVAdjuster` - Abstract base class
- `cvextract.shared.{load_prompt, format_prompt}` - Prompt management
- `cvextract.verifiers.get_verifier` - Schema validation (CV and research)
- `cvextract.contracts.research_schema.json` - Research data schema
- `cvextract.contracts.cv_schema.json` - CV data schema

### External Dependencies

- `openai` (>= 1.0) - OpenAI API client
- `requests` - HTTP client for web page fetching

### Integration Points

- Registered in `cvextract/adjusters/__init__.py` as `"openai-company-research"`
- Used by `cvextract.pipeline` for adjustment stage
- Cache managed by `cvextract/adjusters/openai_company_research_adjuster.py`

## Test Coverage

Tested in:
- `tests/test_adjusters.py` - Adjuster integration tests
- `tests/test_cli_execute.py` - Adjustment flow without cache injection
- `tests/test_cli_parallel.py` - Upfront research and cache reuse

## Implementation Details

### Cache Filename Generation

```python
def url_to_cache_filename(url: str) -> str:
    """Convert URL to safe filename (from cvextract.shared)."""
    # Extract domain: https://www.example.com/path → example.com
    # Add hash for uniqueness: example.com-abc12345.research.json
```

### Research Validation

Research data is validated using `CompanyProfileVerifier` before caching:

```python
verifier = get_verifier("company-profile-verifier")
is_valid, _ = verifier.verify(research_data)
if is_valid:
    cache_research(research_data)
```

### CV Validation

Adjusted CV is validated using `CVSchemaVerifier` before returning:

```python
verifier = get_verifier("cv-schema-verifier")
is_valid, _ = verifier.verify(adjusted_cv)
if not is_valid:
    return original_cv  # Fallback
```

## Performance Characteristics

- **Research Time**: 5-15 seconds per company (first time)
- **Adjustment Time**: 3-10 seconds per CV
- **Cache Reuse**: < 1 second (no API calls)
- **Cost**: ~$0.01-0.05 per company research + $0.005-0.02 per CV adjustment (with gpt-4o-mini)

## Limitations

- **Web Scraping**: Limited to publicly accessible pages
- **Content Extraction**: Quality depends on website structure and content
- **API Costs**: Requires OpenAI API calls (mitigated by caching)
- **Network Required**: Cannot work offline
- **Rate Limits**: Subject to OpenAI API rate limits

## Use Cases

**Best For**:
- Tailoring CVs for specific client proposals
- Batch processing CVs for target companies
- Scenarios where company research can be reused

**Not Suitable For**:
- Offline environments
- Companies with minimal web presence
- Scenarios requiring up-to-the-second company information

## File Paths

- Implementation: `cvextract/adjusters/openai_company_research_adjuster.py`
- Base Class: `cvextract/adjusters/base.py`
- Registry: `cvextract/adjusters/adjuster_registry.py`
- Prompts:
  - `cvextract/adjusters/prompts/website_analysis_prompt.md` - Company research prompt
  - `cvextract/adjusters/prompts/adjuster_promp_for_a_company.md` - CV adjustment prompt
- Research Schema: `cvextract/contracts/research_schema.json`
- CV Schema: `cvextract/contracts/cv_schema.json`
- Tests: `tests/test_adjusters.py`

## Related Documentation

- [Adjustment Architecture](../README.md)
- [Job-Specific Adjuster](../job-specific-adjuster/README.md) - Alternative adjustment strategy
- [Named Adjusters](../named-adjusters/README.md) - Registry system
- [Adjuster Chaining](../adjuster-chaining/README.md) - Sequential application
- [Company Profile Verifier](../../verification/company-profile-verifier/README.md) - Research validation
- Module README: `cvextract/adjusters/README.md`
