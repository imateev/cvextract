# CV Schema

## Overview

The CV schema (`cv_schema.json`) defines the formal JSON Schema for all CV data produced and consumed by cvextract.

## Status

**Active** - Core data contract

## Description

The schema defines:
1. **Required Fields**: Top-level sections that must be present
2. **Data Types**: String vs array vs object for each field
3. **Structure**: Nesting and organization of CV data
4. **Validation Rules**: Format and content requirements

## Entry Points

### Schema File

Location: `cvextract/contracts/cv_schema.json`

### Programmatic Validation

```python
from typing import Any, Dict
from cvextract.verifiers import get_verifier

cv_data: Dict[str, Any] = {...}
verifier = get_verifier("cv-schema-verifier")
result = verifier.verify(data=cv_data)

if not result.ok:
    print(f"Schema violations: {result.errors}")
```

### Schema Loading

```python
from pathlib import Path
import json

schema_path = Path(__file__).parent.parent / "contracts" / "cv_schema.json"
with open(schema_path) as f:
    schema = json.load(f)
```

## Schema Structure

### Top-Level

```json
{
  "type": "object",
  "required": ["identity", "sidebar", "overview", "experiences"],
  "properties": {
    "identity": {...},
    "sidebar": {...},
    "overview": {...},
    "experiences": {...}
  }
}
```

### Identity Section

```json
{
  "type": "object",
  "required": ["title", "full_name", "first_name", "last_name"],
  "properties": {
    "title": {"type": "string"},
    "full_name": {"type": "string"},
    "first_name": {"type": "string"},
    "last_name": {"type": "string"}
  }
}
```

### Sidebar Section

```json
{
  "type": "object",
  "properties": {
    "languages": {"type": "array", "items": {"type": "string"}},
    "tools": {"type": "array", "items": {"type": "string"}},
    "certifications": {"type": "array", "items": {"type": "string"}},
    "industries": {"type": "array", "items": {"type": "string"}},
    "spoken_languages": {"type": "array", "items": {"type": "string"}},
    "academic_background": {"type": "array", "items": {"type": "string"}}
  }
}
```

### Overview Section

```json
{
  "type": "string"
}
```

### Experiences Section

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "required": ["heading", "description", "bullets"],
    "properties": {
      "heading": {"type": "string"},
      "description": {"type": "string"},
      "bullets": {
        "type": "array",
        "items": {"type": "string"}
      },
      "environment": {
        "type": ["array", "null"],
        "items": {"type": "string"}
      }
    }
  }
}
```

## Interfaces

### Producers (Must Conform)

- `cvextract.extractors.DocxCVExtractor`
- `cvextract.extractors.OpenAICVExtractor`
- All custom extractors

### Consumers (Expect Conformance)

- `cvextract.renderers.DocxCVRenderer`
- `cvextract.adjusters.*` (all adjusters)
- `cvextract.verifiers.CVSchemaVerifier`
- All templates in `examples/templates/`

### Validators

- `cvextract.verifiers.CVSchemaVerifier` - Runtime validation

## Dependencies

### Internal Dependencies

- Used by all extractors (produce conforming data)
- Used by all adjusters (preserve schema)
- Used by all renderers (consume conforming data)
- Used by `CVSchemaVerifier` for validation

### External Dependencies

- Validated using `jsonschema` library (Draft 7 JSON Schema)

### Integration Points

- Referenced in extractor documentation
- Referenced in renderer templates
- Used in test fixtures
- Used in example data files

## Test Coverage

Tested in:
- `tests/test_contracts.py` - Schema validation tests
- `tests/test_verifiers.py` - CVSchemaVerifier tests
- `tests/test_extractors.py` - Extractor output validation
- `tests/test_renderers.py` - Renderer input validation

## Implementation History

The CV schema was defined in the initial implementation and has remained stable, ensuring backward compatibility.

**Key Files**:
- `cvextract/contracts/cv_schema.json` - Schema definition
- `cvextract/verifiers/default_cv_schema_verifier.py` - Runtime validator

## Open Questions

1. **Versioning**: Should we version the schema (e.g., v1, v2)?
2. **Extensions**: Should we support custom field extensions?
3. **Strict Mode**: Should we enforce additional constraints (min lengths, patterns)?
4. **Evolution**: How do we handle schema changes without breaking existing data?

## Example Valid Data

```json
{
  "identity": {
    "title": "Senior Software Engineer",
    "full_name": "John Doe",
    "first_name": "John",
    "last_name": "Doe"
  },
  "sidebar": {
    "languages": ["Python", "Java", "Go"],
    "tools": ["Docker", "Kubernetes", "Terraform"],
    "certifications": ["AWS Solutions Architect"],
    "industries": ["Finance", "Healthcare"],
    "spoken_languages": ["English", "Spanish"],
    "academic_background": ["BS Computer Science", "MS Software Engineering"]
  },
  "overview": "Experienced software engineer with 10+ years...",
  "experiences": [
    {
      "heading": "2020 - Present | Senior Engineer at TechCorp",
      "description": "Leading backend development team...",
      "bullets": [
        "Designed and implemented microservices architecture",
        "Reduced latency by 40% through optimization"
      ],
      "environment": ["Python", "AWS", "PostgreSQL"]
    }
  ]
}
```

## File Paths

- Schema: `cvextract/contracts/cv_schema.json`
- Validator: `cvextract/verifiers/default_cv_schema_verifier.py`
- Tests: `tests/test_contracts.py`
- Documentation: `cvextract/contracts/README.md`

## Related Documentation

- [Contracts Architecture](../README.md)
- [Research Schema](../research-schema/README.md)
- [Schema Verifier](../../verification/schema-verifier/README.md)
- Module README: `cvextract/contracts/README.md`
