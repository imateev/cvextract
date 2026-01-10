# Contracts

This directory contains JSON Schema files that define the data structures and contracts used throughout the cvextract application.

## Schemas

### cv_schema.json

Defines the structure for CV (Curriculum Vitae) data extracted from documents and used for rendering.

**Structure:**
- `identity`: Personal information (title, full_name, first_name, last_name)
- `sidebar`: Categorized lists (languages, tools, certifications, industries, spoken_languages, academic_background)
- `overview`: Free-text overview section
- `experiences`: List of professional experience entries

**Used by:**
- `verifiers.DefaultCvSchemaVerifier` - Validates CV data
- `extractors.DocxCVExtractor` - Produces data conforming to this schema
- All registered renderers (e.g., `"default-docx-cv-renderer"`) - Consume data conforming to this schema

### research_schema.json

Defines the structure for company research data used in ML-based CV adjustment.

**Structure:**
- `name`: Company name
- `description`: Company description
- `domains`: Business domains/industries
- `technology_signals`: Technologies of interest to the company
- `acquisition_history`: Past acquisitions and ownership changes
- `rebranded_from`: Previous company names
- `owned_products`: Products/services owned by the company
- `used_products`: Products/tools used by the company

**Used by:**
- `ml_adjustment.MLAdjuster` - Uses this schema for company research
- Research caching functionality

## Usage

Schemas are automatically loaded by the relevant modules using relative paths:

```python
# In verifiers/default_cv_schema_verifier.py
schema_path = Path(__file__).parent.parent / "contracts" / "cv_schema.json"

# In ml_adjustment/adjuster.py
schema_path = Path(__file__).parent.parent / "contracts" / "research_schema.json"
```

## Maintenance

When updating schemas:
1. Ensure backward compatibility or update all consuming modules
2. Update documentation in this README
3. Run all tests to verify nothing breaks
4. Consider adding version information if making breaking changes
