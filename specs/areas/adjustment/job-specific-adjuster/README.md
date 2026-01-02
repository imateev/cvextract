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

## Entry Points

### Programmatic API

```python
from cvextract.adjusters import get_adjuster

# Using job URL
adjuster = get_adjuster("openai-job-specific", model="gpt-4o-mini")
adjusted_cv = adjuster.adjust(
    cv_data,
    job_url="https://careers.example.com/job/123"
)

# Using job description directly
adjusted_cv = adjuster.adjust(
    cv_data,
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
  --apply template=template.docx \
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
- `cvextract.ml_adjustment` - ML adjustment logic
- `cvextract.contracts.cv_schema.json` - CV schema

### External Dependencies

- `openai` (>= 1.0) - OpenAI API client
- `requests` - For fetching job posting URLs

### Integration Points

- Registered as `"openai-job-specific"` in `cvextract/adjusters/__init__.py`
- Used by `cvextract.cli_execute` when `--adjust name=openai-job-specific`
- Can be chained with other adjusters

## Test Coverage

Tested in:
- `tests/test_adjusters.py` - Unit and integration tests
- `tests/test_cli.py` - CLI integration

## Implementation History

The job-specific adjuster was added to complement the company research adjuster, enabling dual optimization (company + specific role).

**Key Files**:
- `cvextract/adjusters/openai_job_specific_adjuster.py` - Implementation
- `cvextract/ml_adjustment/prompts/job_specific_prompt.md` - Adjustment prompt

## Open Questions

1. **Job Caching**: Should we cache job description research like company research?
2. **Combined Mode**: Should we support combined company+job adjustment in one adjuster?
3. **Skills Matching**: Should we add explicit skills matching/scoring?

## File Paths

- Implementation: `cvextract/adjusters/openai_job_specific_adjuster.py`
- Prompt: `cvextract/ml_adjustment/prompts/job_specific_prompt.md`
- Tests: `tests/test_adjusters.py`
- Documentation: `cvextract/adjusters/README.md`

## Related Documentation

- [Adjustment Architecture](../README.md)
- [Named Adjusters](../named-adjusters/README.md)
- [Adjuster Chaining](../adjuster-chaining/README.md)
- Module README: `cvextract/adjusters/README.md`
