# Extracted Data Verifier

## Overview

The extracted data verifier validates completeness and basic structure of extracted CV data, checking for required fields and data quality issues.

## Status

**Active** - Core verification component

## Description

The `DefaultExpectedCvDataVerifier` class checks:
1. Presence of all top-level sections (identity, sidebar, overview, experiences)
2. Identity completeness (title, names)
3. Sidebar category population
4. Experience entry structure (heading, bullets)
5. Data type correctness (lists vs strings)

## Entry Points

### Programmatic API

```python
from pathlib import Path
from cvextract.cli_config import UserConfig
from cvextract.shared import UnitOfWork
from cvextract.verifiers import get_verifier

cv_path = Path("cv.json")
work = UnitOfWork(config=UserConfig(target_dir=cv_path.parent), input=cv_path, output=cv_path)
verifier = get_verifier("default-extract-verifier")
result = verifier.verify(work)

if result.ok:
    print("Data is valid!")
else:
    print(f"Errors: {result.errors}")
    print(f"Warnings: {result.warnings}")
```

### Pipeline Integration

Used automatically in `cvextract.pipeline` after extraction:

```python
from pathlib import Path
from cvextract.cli_execute_extract import execute as execute_extract
from cvextract.shared import UnitOfWork
from cvextract.cli_config import UserConfig, ExtractStage

# Verification happens internally
work = UnitOfWork(
    config=UserConfig(target_dir=Path("out"), extract=ExtractStage(source=source_path)),
    input=source_path,
    output=None,
)
result = execute_extract(work)
```

## Configuration

No configuration required - validates against hardcoded completeness rules.

## Interfaces

### Input

- **UnitOfWork**: input/output paths with JSON output to validate

### Output

- **UnitOfWork**: Step status updated with `errors` and `warnings`

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
- `cvextract.shared.UnitOfWork` - Result container

### Integration Points

- Used in `cvextract.cli_execute_extract.execute()`
- Results logged in pipeline

## Test Coverage

Tested in:
- `tests/test_verifiers.py` - Unit tests
- `tests/test_pipeline.py` - Integration tests

## Implementation History

The data verifier was part of the initial implementation to ensure extraction quality.

**Key Files**:
- `cvextract/verifiers/default_expected_cv_data_verifier.py` - Implementation
- `cvextract/verifiers/base.py` - Base class

## File Paths

- Implementation: `cvextract/verifiers/default_expected_cv_data_verifier.py`
- Base Class: `cvextract/verifiers/base.py`
- Tests: `tests/test_verifiers.py`
- Documentation: `cvextract/verifiers/README.md`

## Related Documentation

- [Verification Architecture](../README.md)
- [Schema Verifier](../schema-verifier/README.md)
- [Roundtrip Verifier](../comparison-verifiers/README.md)
- Module README: `cvextract/verifiers/README.md`
