# Schema Verifier

## Overview

The schema verifier validates CV data against the formal JSON Schema definition, ensuring strict conformance to the data contract.

## Status

**Active** - Core verification component

## Description

The `DefaultCvSchemaVerifier` class:
1. Loads JSON Schema from `cvextract/contracts/cv_schema.json`
2. Validates CV data against schema structure
3. Reports schema violations as errors
4. Supports custom schema paths for testing

## Entry Points

### Programmatic API

```python
from pathlib import Path
from cvextract.cli_config import UserConfig
from cvextract.shared import StepName, UnitOfWork
from cvextract.verifiers import get_verifier

cv_path = Path("cv.json")
work = UnitOfWork(config=UserConfig(target_dir=cv_path.parent), input=cv_path, output=cv_path)
work.current_step = StepName.Extract
work.ensure_step_status(StepName.VerifyExtract)

# Use default schema
verifier = get_verifier("cv-schema-verifier")
result = verifier.verify(work)

# Use custom schema
verifier = get_verifier("cv-schema-verifier", schema_path=Path("custom_schema.json"))
result = verifier.verify(work)
```

### Pipeline Integration

Can be used alongside other verifiers:

```python
from pathlib import Path
from cvextract.cli_config import UserConfig
from cvextract.shared import StepName, UnitOfWork
from cvextract.verifiers import get_verifier

cv_path = Path("cv.json")
work = UnitOfWork(config=UserConfig(target_dir=cv_path.parent), input=cv_path, output=cv_path)
work.current_step = StepName.Extract
work.ensure_step_status(StepName.VerifyExtract)

# First check schema
schema_verifier = get_verifier("cv-schema-verifier")
schema_result = schema_verifier.verify(work)

# Then check completeness
data_verifier = get_verifier("default-extract-verifier")
data_result = data_verifier.verify(work)
```

## Configuration

### Parameters

- **schema_path** (optional): Path to JSON Schema file
  - Default: `cvextract/contracts/cv_schema.json`

## Interfaces

### Input

- **UnitOfWork**: input/output paths with JSON output to validate

### Output

- **UnitOfWork**: Step status updated with validation errors and warnings
- Errors contain JSON Schema validation messages

### Schema Structure

The CV schema (`cv_schema.json`) defines:

```json
{
  "type": "object",
  "required": ["identity", "sidebar", "overview", "experiences"],
  "properties": {
    "identity": {
      "type": "object",
      "required": ["title", "full_name", "first_name", "last_name"],
      "properties": {...}
    },
    "sidebar": {
      "type": "object",
      "properties": {
        "languages": {"type": "array", "items": {"type": "string"}},
        ...
      }
    },
    ...
  }
}
```

## Dependencies

### Internal Dependencies

- `cvextract.verifiers.base.CVVerifier` - Base class
- `cvextract.shared.UnitOfWork` - Result container
- `cvextract/contracts/cv_schema.json` - Schema definition

### External Dependencies

None - uses basic Python structure validation

### Integration Points

- Can be used in pipeline (currently optional)
- Used in testing to validate test fixtures
- Future: Could be made mandatory in strict mode

## Test Coverage

Tested in:
- `tests/test_verifiers.py` - Unit tests with valid/invalid data
- `tests/test_contracts.py` - Schema itself validation

## Implementation History

Schema validation was added to provide formal contract enforcement beyond basic completeness checks.

**Key Files**:
- `cvextract/verifiers/default_cv_schema_verifier.py` - Implementation
- `cvextract/contracts/cv_schema.json` - Schema definition
- `cvextract/verifiers/base.py` - Base class

## Open Questions

1. **Mandatory**: Should schema verification be mandatory for all extractions?
2. **Version**: Should we version the schema and support multiple versions?
3. **Extensions**: Should we allow schema extensions for custom fields?
4. **Performance**: Is schema validation too slow for batch processing?

## File Paths

- Implementation: `cvextract/verifiers/default_cv_schema_verifier.py`
- Schema: `cvextract/contracts/cv_schema.json`
- Base Class: `cvextract/verifiers/base.py`
- Tests: `tests/test_verifiers.py`
- Documentation: `cvextract/verifiers/README.md`

## Related Documentation

- [Verification Architecture](../README.md)
- [Extracted Data Verifier](../extracted-data-verifier/README.md)
- [CV Schema](../../contracts/cv-schema/README.md)
- Module README: `cvextract/verifiers/README.md`
