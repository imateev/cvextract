# Adjustment Area

## Purpose

The adjustment area provides ML-based CV optimization and transformation capabilities to tailor CV content for specific companies, jobs, or other contexts.

## Features

- [ML Adjustment](ml-adjustment/README.md) - Core ML-based CV adjustment using OpenAI
- [Company Research & Caching](company-research-caching/README.md) - Automated company research with JSON caching
- [Named Adjusters](named-adjusters/README.md) - Registry-based adjuster lookup system
- [Job-Specific Adjuster](job-specific-adjuster/README.md) - Optimizes CV for specific job postings
- [Adjuster Chaining](adjuster-chaining/README.md) - Sequential application of multiple adjusters

## Architectural Notes

### Design Principles

1. **Pluggable Architecture**: All adjusters implement the `CVAdjuster` abstract base class
2. **Registry Pattern**: Adjusters are registered by name and retrieved via factory functions
3. **Schema Preservation**: Adjusters never add/remove fields from CV schema
4. **Fail-Safe**: On errors, adjusters return original unadjusted data
5. **Chainable**: Multiple adjusters can be applied sequentially

### Key Components

- **Base Interface**: `cvextract/adjusters/base.py` - `CVAdjuster` abstract base class
- **Registry**: `cvextract/adjusters/__init__.py` - Registration and lookup functions
- **Implementations**:
  - `cvextract/adjusters/openai_company_research_adjuster.py` - Company-based adjustment
  - `cvextract/adjusters/openai_job_specific_adjuster.py` - Job-based adjustment
- **ML Module**: `cvextract/ml_adjustment/` - Core ML adjustment logic

### Data Flow

```
Original CV JSON
    │
    v
[Adjuster.adjust(cv_data, **params)]
    │
    ├──> Company Research (cached)
    │
    v
Adjusted CV JSON (reordered, emphasized)
    │
    v
Next Adjuster (if chained)
```

### Integration Points

- **CLI**: `--adjust name=<adjuster> <params...>` (can be repeated for chaining)
- **Pipeline**: Adjusters are applied between extraction and rendering
- **Caching**: Research results cached in `{target}/research_data/`

## Dependencies

- **Internal**: `cvextract.ml_adjustment` (ML logic), `cvextract.contracts` (schemas)
- **External**: `openai` (>= 1.0), `requests` (for web scraping)

## File References

- Base: `cvextract/adjusters/base.py`
- Registry: `cvextract/adjusters/__init__.py`
- Company Adjuster: `cvextract/adjusters/openai_company_research_adjuster.py`
- Job Adjuster: `cvextract/adjusters/openai_job_specific_adjuster.py`
- ML Module: `cvextract/ml_adjustment/adjuster.py`
- Documentation: `cvextract/adjusters/README.md`, `cvextract/ml_adjustment/README.md`
