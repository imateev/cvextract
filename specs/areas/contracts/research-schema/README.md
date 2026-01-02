# Research Schema

## Overview

The research schema (`research_schema.json`) defines the formal JSON Schema for company research data produced by ML adjustment.

## Status

**Active** - ML adjustment data contract

## Description

The schema defines structure for company research results:
1. **Company Information**: Name, description, domains
2. **Technology Signals**: Technologies and their importance scores
3. **Corporate History**: Acquisitions, rebrandings
4. **Product Ecosystem**: Owned and used products

## Entry Points

### Schema File

Location: `cvextract/contracts/research_schema.json`

### Programmatic Usage

```python
from cvextract.ml_adjustment import MLAdjuster
from pathlib import Path

adjuster = MLAdjuster()

# Research is cached conforming to research_schema.json
adjusted = adjuster.adjust(
    cv_data=cv_data,
    target_url="https://example.com",
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
  "required": ["name", "description", "domains", "technology_signals"],
  "properties": {
    "name": {"type": "string"},
    "description": {"type": "string"},
    "domains": {...},
    "technology_signals": {...},
    "acquisition_history": {...},
    "rebranded_from": {...},
    "owned_products": {...},
    "used_products": {...}
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
    "type": "object",
    "patternProperties": {
      ".*": {
        "type": "integer",
        "minimum": 1,
        "maximum": 5
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

- `cvextract.ml_adjustment.MLAdjuster._research_company()` - Produces research data
- `cvextract.adjusters.OpenAICompanyResearchAdjuster` - Uses MLAdjuster

### Consumers (Expect Conformance)

- `cvextract.ml_adjustment.MLAdjuster.adjust()` - Consumes research for CV adjustment
- Research cache files in `{target}/research_data/`

### Validation

Research data is validated before caching to ensure schema conformance.

## Dependencies

### Internal Dependencies

- Produced by `cvextract.ml_adjustment.MLAdjuster`
- Consumed by CV adjustment logic
- Cached in research_data directories

### External Dependencies

- Generated via OpenAI API responses

### Integration Points

- Used in company research adjuster
- Cached for reuse across multiple CVs
- Validated before caching

## Test Coverage

Tested in:
- `tests/test_ml_adjustment.py` - Research generation tests
- `tests/test_contracts.py` - Schema validation tests
- `tests/test_adjusters.py` - Research consumption tests

## Implementation History

The research schema was created alongside the ML adjustment feature to ensure consistent research data structure.

**Key Files**:
- `cvextract/contracts/research_schema.json` - Schema definition
- `cvextract/ml_adjustment/adjuster.py` - Research producer/consumer

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
- Producer: `cvextract/ml_adjustment/adjuster.py`
- Tests: `tests/test_contracts.py`, `tests/test_ml_adjustment.py`
- Documentation: `cvextract/contracts/README.md`

## Related Documentation

- [Contracts Architecture](../README.md)
- [CV Schema](../cv-schema/README.md)
- [ML Adjustment](../../adjustment/ml-adjustment/README.md)
- [Company Research & Caching](../../adjustment/company-research-caching/README.md)
- Module README: `cvextract/contracts/README.md`
