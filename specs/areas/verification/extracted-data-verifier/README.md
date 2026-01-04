# Extracted Data Verifier

## Overview

The extracted data verifier validates completeness and basic structure of extracted CV data, checking for required fields and data quality issues.

## Status

**Active** - Core verification component

## Description

The `ExtractedDataVerifier` class checks:
1. Presence of all top-level sections (identity, sidebar, overview, experiences)
2. Identity completeness (title, names)
3. Sidebar category population
4. Experience entry structure (heading, bullets)
5. Data type correctness (lists vs strings)

## Entry Points

### Programmatic API

```python
from cvextract.verifiers import get_verifier

verifier = get_verifier("private-internal-verifier")
result = verifier.verify(cv_data)

if result.ok:
    print("Data is valid!")
else:
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
```

### Pipeline Integration

Used automatically in `cvextract.pipeline` after extraction:

```python
from cvextract.pipeline_helpers import extract_single

# Verification happens internally
result = extract_single(source_path, extractor, json_output)
```

## Configuration

No configuration required - validates against hardcoded completeness rules.

## Interfaces

### Input

- **data**: CV dictionary conforming to `cvextract/contracts/cv_schema.json`

### Output

- **VerificationResult**: Object with `ok` (bool), `errors` (list), `warnings` (list)

### Validation Rules

**Errors** (cause verification failure):
- Missing top-level sections
- Identity missing name fields
- Experiences not a list
- Experience entries missing required fields

**Warnings** (non-critical issues):
- Empty sidebar categories
- Short/missing overview
- Missing experience descriptions
- Empty bullet lists

## Dependencies

### Internal Dependencies

- `cvextract.verifiers.base.CVVerifier` - Base class
- `cvextract.shared.VerificationResult` - Result type

### Integration Points

- Used in `cvextract.pipeline_helpers.extract_single()`
- Results logged in pipeline
- Affects CLI exit code

## Test Coverage

Tested in:
- `tests/test_verifiers.py` - Unit tests
- `tests/test_pipeline.py` - Integration tests

## Implementation History

The data verifier was part of the initial implementation to ensure extraction quality.

**Key Files**:
- `cvextract/verifiers/data_verifier.py` - Implementation
- `cvextract/verifiers/base.py` - Base class

## File Paths

- Implementation: `cvextract/verifiers/data_verifier.py`
- Base Class: `cvextract/verifiers/base.py`
- Tests: `tests/test_verifiers.py`
- Documentation: `cvextract/verifiers/README.md`

## Related Documentation

- [Verification Architecture](../README.md)
- [Schema Verifier](../schema-verifier/README.md)
- [Comparison Verifiers](../comparison-verifiers/README.md)
- Module README: `cvextract/verifiers/README.md`
