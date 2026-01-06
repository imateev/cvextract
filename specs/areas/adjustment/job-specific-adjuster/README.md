# Job-Specific Adjuster

## Overview

The job-specific adjuster optimizes CV content for specific job postings by analyzing job requirements and highlighting matching experience.

## Status

**Active** - Fully implemented

## Description

The `OpenAIJobSpecificAdjuster` class:
1. Accepts job posting URL or direct job description text
2. Analyzes job requirements and responsibilities
3. Reorders CV content to emphasize relevant experience
4. Adjusts terminology to match job description
5. Maintains factual accuracy (no invention)
6. **Validates adjusted CV against CV schema before returning**

## Entry Points

### Programmatic API

```python
from pathlib import Path
from cvextract.adjusters import get_adjuster
from cvextract.cli_config import UserConfig, ExtractStage
from cvextract.shared import UnitOfWork

# Using job URL
adjuster = get_adjuster("openai-job-specific", model="gpt-4o-mini")
work = UnitOfWork(
    config=UserConfig(target_dir=Path("out"), extract=ExtractStage(source=Path("cv.json"))),
    input=Path("cv.json"),
    output=Path("cv.json"),
)
adjusted_cv = adjuster.adjust(
    work,
    job_url="https://careers.example.com/job/123"
)

# Using job description directly
adjusted_cv = adjuster.adjust(
    work,
    job_description="Senior Software Engineer position..."
)
```

### CLI Usage

```bash
export OPENAI_API_KEY="sk-proj-..."

# Using job URL
python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-job-specific job-url=https://careers.example.com/job/123 \
  --render template=template.docx \
  --target output/

# Using job description
python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-job-specific job-description="Senior Engineer..." \
  --target output/
```

## Configuration

### Parameters

- **`job-url`** (required if no job-description): URL of job posting
- **`job-description`** (required if no job-url): Direct text of job description
- **`openai-model`** (optional): OpenAI model name, defaults to `gpt-4o-mini`

### Environment Variables

- **`OPENAI_API_KEY`** (required): OpenAI API key
- **`OPENAI_MODEL`** (optional): Default model name

## Interfaces

### Input

- CV JSON data + either `job_url` or `job_description`

### Output

- Adjusted CV JSON with job-optimized content

## Dependencies

### Internal Dependencies

- `cvextract.adjusters.base.CVAdjuster` - Base class
- `cvextract.shared.format_prompt` - Prompt formatting
- `cvextract.verifiers.get_verifier` - Schema validation
- `cvextract.contracts.cv_schema.json` - CV schema

### External Dependencies

- `openai` (>= 1.0) - OpenAI API client
- `requests` - For fetching job posting URLs

### Integration Points

- Registered as `"openai-job-specific"` in `cvextract/adjusters/__init__.py`
- Used by `cvextract.cli_execute_adjust.execute()` when `--adjust name=openai-job-specific`
- Can be chained with other adjusters

## Test Coverage

Tested in:
- `tests/test_adjusters.py` - Unit and integration tests (39 tests, 98% coverage)
  - Happy path adjustments with valid job descriptions
  - Schema validation success and failure scenarios
  - Rate limit handling with exponential backoff
  - Job description fetching from URLs with HTML cleaning
  - Error handling and fallback to original CV
- `tests/test_cli.py` - CLI integration

## Implementation History

The job-specific adjuster was added to complement the company research adjuster, enabling dual optimization (company + specific role).

**Key Files**:
- `cvextract/adjusters/openai_job_specific_adjuster.py` - Implementation
- `cvextract/adjusters/prompts/adjuster_promp_for_specific_job.md` - Adjustment prompt

## Open Questions

1. **Job Caching**: Should we cache job description research like company research?
2. **Combined Mode**: Should we support combined company+job adjustment in one adjuster?
3. **Skills Matching**: Should we add explicit skills matching/scoring?

## File Paths

- Implementation: `cvextract/adjusters/openai_job_specific_adjuster.py`
- Prompt: `cvextract/adjusters/prompts/adjuster_promp_for_specific_job.md`
- Tests: `tests/test_adjusters.py`
- Documentation: `cvextract/adjusters/README.md`

## Related Documentation

- [Adjustment Architecture](../README.md)
- [Named Adjusters](../named-adjusters/README.md)
- [Adjuster Chaining](../adjuster-chaining/README.md)
- Module README: `cvextract/adjusters/README.md`
