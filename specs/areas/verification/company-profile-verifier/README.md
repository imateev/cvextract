# Company Profile Verifier

## Overview

The company profile verifier validates company research data against the formal JSON Schema definition, ensuring strict conformance to the research data contract.

## Status

**Active** - Core verification component

## Description

The `CompanyProfileVerifier` class:
1. Loads JSON Schema from `cvextract/contracts/research_schema.json`
2. Validates company profile data using schema validation
3. Reports schema violations as errors
4. Supports custom schema paths for testing
5. Used by ML adjustment module to validate research data

## Entry Points

### Programmatic API

```python
from cvextract.verifiers import get_verifier
from pathlib import Path

# Use default schema
verifier = get_verifier("company-profile-verifier")
result = verifier.verify(company_data)

# Use custom schema
verifier = CompanyProfileVerifier(schema_path=Path("custom_research_schema.json"))
result = verifier.verify(company_data)
```

### Integration Points

Used by `cvextract.adjusters.openai_company_research_adjuster._validate_research_data()` to validate company research before caching and using in adjustments.

## Configuration

### Parameters

- **schema_path** (optional): Path to JSON Schema file
  - Default: `cvextract/contracts/research_schema.json`

## Interfaces

### Input

- **data**: Company profile dictionary to validate

### Output

- **VerificationResult**: Object with `ok`, `errors`, `warnings`
- Errors contain schema validation messages

### Schema Structure

The research schema (`research_schema.json`) defines:

```json
{
  "type": "object",
  "required": ["name", "domains"],
  "properties": {
    "name": {
      "type": "string",
      "description": "Legal or commonly used name of the company"
    },
    "domains": {
      "type": "array",
      "items": {"type": "string"},
      "minItems": 1,
      "uniqueItems": true,
      "description": "Industries or sectors the company operates in"
    },
    "description": {
      "type": "string",
      "description": "High-level company description"
    },
    "technology_signals": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["technology"],
        "properties": {
          "technology": {"type": "string"},
          "category": {"type": "string"},
          "interest_level": {"enum": ["low", "medium", "high"]},
          "confidence": {"type": "number", "minimum": 0, "maximum": 1},
          "signals": {"type": "array", "items": {"type": "string"}},
          "notes": {"type": "string"}
        }
      }
    },
    "founded_year": {
      "type": "integer",
      "minimum": 1600,
      "maximum": 2100
    },
    "headquarters": {
      "type": "object",
      "required": ["country"],
      "properties": {
        "city": {"type": "string"},
        "state": {"type": "string"},
        "country": {"type": "string"}
      }
    },
    "company_size": {
      "enum": ["solo", "small", "medium", "large", "enterprise"]
    },
    "employee_count": {
      "type": "integer",
      "minimum": 1
    },
    "ownership_type": {
      "enum": ["private", "public", "nonprofit", "government"]
    },
    "website": {
      "type": "string"
    }
  }
}
```

## Dependencies

### Internal Dependencies

- `cvextract.verifiers.base.CVVerifier` - Base class
- `cvextract.shared.VerificationResult` - Result type
- `cvextract/contracts/research_schema.json` - Schema definition

### External Dependencies

None - uses only standard library JSON

### Integration Points

- Used by `cvextract.adjusters.OpenAICompanyResearchAdjuster`
- Ensures company research data quality before caching and usage

## Test Coverage

Tested in:
- `tests/test_company_profile_verifier.py` - 22 unit tests covering:
  - Valid minimal and full profiles
  - Required field validation
  - Type validation for all fields
  - Enum validation (company_size, ownership_type, interest_level)
  - Nested object validation (technology_signals, headquarters)
  - Optional field handling (None values)
  - Registry access via `get_verifier("company-profile-verifier")`

## Usage Example

```python
from cvextract.verifiers import get_verifier

# Get the verifier from registry
verifier = get_verifier("company-profile-verifier")

# Validate company profile
company_data = {
    "name": "Tech Corporation",
    "domains": ["AI", "Cloud Computing"],
    "description": "Leading technology company",
    "founded_year": 2010,
    "company_size": "large",
    "headquarters": {
        "city": "San Francisco",
        "state": "CA",
        "country": "USA"
    }
}

result = verifier.verify(company_data)
if result.ok:
    print("Company profile is valid")
else:
    print(f"Validation errors: {result.errors}")
```

## Related Features

- [CV Schema Verifier](../schema-verifier/README.md) - Validates CV data
- [Verifier Registry](../verifier-registry/README.md) - Registry system for verifiers
- [Company Research & Caching](../../adjustment/company-research-caching/README.md) - Uses this verifier
