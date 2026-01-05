# Research Schema

## Overview

The research schema (`research_schema.json`) defines the formal JSON Schema for company research data produced by the company research adjuster.

## Status

**Active** - Company research data contract

## Description

The schema defines structure for company research results:
1. **Company Information**: Name, description, domains
2. **Technology Signals**: Technologies with categories, interest levels, and confidence scores
3. **Industry Classification**: NAICS/SIC codes
4. **Corporate Details**: Founded year, headquarters, size, ownership
5. **Historical Information**: Acquisition history, rebranding
6. **Product Ecosystem**: Owned products, used products, related companies

## Entry Points

### Schema File

Location: `cvextract/contracts/research_schema.json`

### Programmatic Usage

```python
from pathlib import Path
from cvextract.adjusters import OpenAICompanyResearchAdjuster
from cvextract.cli_config import UserConfig, ExtractStage
from cvextract.shared import UnitOfWork

adjuster = OpenAICompanyResearchAdjuster()

# Research is cached conforming to research_schema.json
work = UnitOfWork(
    config=UserConfig(target_dir=Path("out"), extract=ExtractStage(source=Path("cv.json"))),
    input=Path("cv.json"),
    output=Path("cv.json"),
)
adjusted = adjuster.adjust(
    work,
    customer_url="https://example.com",
    cache_path=Path("cache/example.research.json")
)
```

### Schema Loading

```python
from pathlib import Path
import json

schema_path = Path(__file__).parent.parent / "contracts" / "research_schema.json"
with open(schema_path) as f:
    schema = json.load(f)
```

## Schema Structure

### Top-Level

```json
{
  "type": "object",
  "required": ["name", "domains"],
  "properties": {
    "name": {"type": "string"},
    "description": {"type": "string"},
    "domains": {...},
    "technology_signals": {...},
    "industry_classification": {...},
    "founded_year": {...},
    "headquarters": {...},
    "company_size": {...},
    "employee_count": {...},
    "ownership_type": {...},
    "website": {...},
    "tags": {...},
    "confidence_score": {...},
    "acquisition_history": {...},
    "rebranded_from": {...},
    "owned_products": {...},
    "used_products": {...},
    "related_companies": {...}
  }
}
```

### Company Information

```json
{
  "name": {"type": "string"},
  "description": {"type": "string"},
  "domains": {
    "type": "array",
    "items": {"type": "string"}
  }
}
```

### Technology Signals

```json
{
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
  }
}
```

Importance scale: 1 (low) to 5 (critical)

### Corporate History

```json
{
  "acquisition_history": {
    "type": "array",
    "items": {"type": "string"}
  },
  "rebranded_from": {
    "type": "array",
    "items": {"type": "string"}
  }
}
```

### Product Ecosystem

```json
{
  "owned_products": {
    "type": "array",
    "items": {"type": "string"}
  },
  "used_products": {
    "type": "array",
    "items": {"type": "string"}
  }
}
```

## Interfaces

### Producers (Must Conform)

- `cvextract.adjusters.OpenAICompanyResearchAdjuster` - Produces and caches research data
- Internal research methods that fetch and structure company information

### Consumers (Expect Conformance)

- `cvextract.adjusters.OpenAICompanyResearchAdjuster.adjust()` - Consumes research for CV adjustment
- Research cache files in `{target}/research_data/`

### Validation

Research data is validated using `CompanyProfileVerifier` before caching to ensure schema conformance.

## Dependencies

### Internal Dependencies

- Produced by `cvextract.adjusters.OpenAICompanyResearchAdjuster`
- Validated by `cvextract.verifiers.CompanyProfileVerifier`
- Consumed by CV adjustment logic
- Cached in research_data directories

### External Dependencies

- Generated via OpenAI API responses

### Integration Points

- Used in company research adjuster
- Cached for reuse across multiple CVs
- Validated before caching using CompanyProfileVerifier

## Test Coverage

Tested in:
- `tests/test_adjusters.py` - Research generation and adjustment tests
- `tests/test_verifiers.py` - Schema validation tests
- `tests/test_pipeline.py` - End-to-end with research caching

## Implementation History

The research schema was created alongside the company research adjuster to ensure consistent research data structure.

**Key Files**:
- `cvextract/contracts/research_schema.json` - Schema definition
- `cvextract/adjusters/openai_company_research_adjuster.py` - Research producer/consumer
- `cvextract/verifiers/company_profile_verifier.py` - Research validator

## Example Valid Data

```json
{
  "name": "TechCorp Inc.",
  "description": "Leading cloud infrastructure provider",
  "domains": ["Cloud Computing", "DevOps", "Enterprise Software"],
  "technology_signals": {
    "Kubernetes": 5,
    "Docker": 5,
    "Python": 4,
    "Go": 4,
    "React": 3,
    "AWS": 5,
    "Terraform": 4
  },
  "acquisition_history": [
    "Acquired ContainerCo in 2021",
    "Acquired DevTools Inc in 2019"
  ],
  "rebranded_from": [
    "CloudStartup (2015-2018)"
  ],
  "owned_products": [
    "TechCorp Cloud Platform",
    "TechCorp Container Registry",
    "TechCorp CLI"
  ],
  "used_products": [
    "GitHub",
    "Jenkins",
    "Datadog",
    "Slack"
  ]
}
```

## File Paths

- Schema: `cvextract/contracts/research_schema.json`
- Producer: `cvextract/adjusters/openai_company_research_adjuster.py`
- Validator: `cvextract/verifiers/company_profile_verifier.py`
- Tests: `tests/test_adjusters.py`, `tests/test_verifiers.py`
- Documentation: `cvextract/contracts/README.md`

## Related Documentation

- [Contracts Architecture](../README.md)
- [CV Schema](../cv-schema/README.md)
- [Company Research Adjuster](../../adjustment/company-research-adjuster/README.md)
- [Company Profile Verifier](../../verification/company-profile-verifier/README.md)
- Module README: `cvextract/contracts/README.md`
