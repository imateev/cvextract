# Company Research & Caching

## Overview

Automated company research with JSON caching enables efficient, cost-effective CV adjustment by researching target companies once and reusing the results.

## Status

**Active** - Integrated with ML adjustment

## Description

The company research feature:
1. Fetches and analyzes company website content
2. Extracts structured company information using OpenAI
3. Caches research results as JSON files
4. Reuses cached data for subsequent CV adjustments
5. Validates research data against schema before caching

## Entry Points

### Programmatic API

```python
from cvextract.ml_adjustment import MLAdjuster
from pathlib import Path

adjuster = MLAdjuster()
adjusted = adjuster.adjust(
    cv_data=cv_data,
    target_url="https://example.com",
    cache_path=Path("cache/example_com.research.json")  # Cached here
)
```

### CLI Usage

```bash
export OPENAI_API_KEY="sk-proj-..."
python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com \
  --target output/

# Research cached at: output/research_data/<cv-name>/example_com.json
```

## Configuration

### Cache Path Determination

- **Automatic**: `{target}/research_data/{cv_name}/{sanitized_url}.json`
- **Manual**: Specify `cache_path` parameter in programmatic API

### Cache Filename Generation

```python
from cvextract.ml_adjustment import _url_to_cache_filename

filename = _url_to_cache_filename("https://www.example.com/about")
# Returns: "example_com-<hash>.research.json"
```

## Interfaces

### Research Schema

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
  "acquisition_history": [...],
  "rebranded_from": [...],
  "owned_products": [...],
  "used_products": [...]
}
```

### Cache Storage

- **Format**: JSON file
- **Validation**: Checked against research schema before caching
- **Reuse**: Subsequent adjustments check cache before making API calls

## Dependencies

### Internal Dependencies

- `cvextract.ml_adjustment.MLAdjuster` - Research performer
- `cvextract.contracts.research_schema.json` - Data validation

### External Dependencies

- `requests` - Web page fetching
- `openai` - Research extraction

### Integration Points

- Used by `cvextract.adjusters.OpenAICompanyResearchAdjuster`
- Cache managed by `cvextract.cli_execute.execute_pipeline()`
- Parallel processing pre-researches in `cvextract.cli_parallel`

## Test Coverage

Tested in:
- `tests/test_ml_adjustment.py` - Caching logic
- `tests/test_pipeline.py` - End-to-end with caching
- `tests/test_cli.py` - CLI cache path generation

## Implementation History

Caching was added to reduce API costs and improve performance for batch processing scenarios.

**Key Files**:
- `cvextract/ml_adjustment/adjuster.py` - Cache read/write logic
- `cvextract/cli_execute.py` - Cache path determination
- `cvextract/cli_parallel.py` - Batch pre-research

## File Paths

- Implementation: `cvextract/ml_adjustment/adjuster.py` (methods: `_research_company`, `adjust`)
- Schema: `cvextract/contracts/research_schema.json`
- Tests: `tests/test_ml_adjustment.py`

## Related Documentation

- [ML Adjustment](../ml-adjustment/README.md)
- [Named Adjusters](../named-adjusters/README.md)
- Module README: `cvextract/ml_adjustment/README.md`
