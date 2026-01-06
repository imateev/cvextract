# Adjustment Area

## Purpose

The adjustment area provides ML-based CV optimization and transformation capabilities to tailor CV content for specific companies, jobs, or other contexts.

## Features

- [Company Research Adjuster](company-research-adjuster/README.md) - OpenAI-based adjustment with company research and caching
- [Job-Specific Adjuster](job-specific-adjuster/README.md) - Optimizes CV for specific job postings
- [Named Adjusters](named-adjusters/README.md) - Registry-based adjuster lookup system
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
- **Registry**: `cvextract/adjusters/adjuster_registry.py` - Registration and lookup functions
- **Implementations**:
  - `cvextract/adjusters/openai_company_research_adjuster.py` - Company-based adjustment
  - `cvextract/adjusters/openai_job_specific_adjuster.py` - Job-based adjustment

### Data Flow

```
Original CV JSON
    │
    v
[Adjuster.adjust(work, **params)]
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

- **Internal**: `cvextract.shared` (prompt loading), `cvextract.contracts` (schemas), `cvextract.verifiers` (schema validation)
- **External**: `openai` (>= 1.0), `requests` (for web scraping)

## File References

- Base: `cvextract/adjusters/base.py`
- Registry: `cvextract/adjusters/adjuster_registry.py`
- Public API: `cvextract/adjusters/__init__.py`
- Company Adjuster: `cvextract/adjusters/openai_company_research_adjuster.py`
- Job Adjuster: `cvextract/adjusters/openai_job_specific_adjuster.py`
- Prompts: `cvextract/adjusters/prompts/`
- Documentation: `cvextract/adjusters/README.md`
