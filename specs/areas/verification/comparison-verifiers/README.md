# Roundtrip Verifier

## Overview

The roundtrip verifier checks equivalence between two CV data structures, primarily used for roundtrip verification (extract → render → extract comparison).

## Status

**Active** - Core verification component

## Description

Implementation:
1. **`RoundtripVerifier`**: Compares JSON files referenced by a `UnitOfWork`

It checks:
- Structural equivalence
- Field-by-field comparison
- Deep equality of nested structures
- List order and contents

## Entry Points

### RoundtripVerifier (File-Based)

```python
from pathlib import Path
from cvextract.cli_config import UserConfig
from cvextract.shared import UnitOfWork
from cvextract.verifiers import get_verifier

verifier = get_verifier("roundtrip-verifier")
source_path = Path("source.json")
target_path = Path("roundtrip.json")
work = UnitOfWork(config=UserConfig(target_dir=source_path.parent), input=source_path, output=target_path)
result = verifier.verify(work)

if result.ok:
    print("Data structures match!")
else:
    print(f"Differences: {result.errors}")
```

### Pipeline Integration

Used in roundtrip verification:

```python
# In pipeline
result = render_and_verify(work)
# Internally uses RoundtripVerifier for roundtrip check
```

## Configuration

### Parameters

- **RoundtripVerifier**: `verify(work)`

## Interfaces

### Input

- **UnitOfWork**: input/output paths for the original and roundtrip JSON

### Output

- **VerificationResult**: Object with `ok`, `errors`, `warnings`
- Errors list specific fields that differ

### Comparison Logic

- Deep comparison of all fields
- Order-sensitive for lists (experiences, bullets)
- Type-sensitive (string vs list, etc.)
- Reports first difference found

## Dependencies

### Internal Dependencies

- `cvextract.verifiers.base.CVVerifier` - Base class
- `cvextract.shared.VerificationResult` - Result type

### Integration Points

- Used in `cvextract.pipeline_helpers.render_and_verify()`
- Results affect roundtrip verification icon in logs
- Skip roundtrip when adjustment is used

## Test Coverage

Tested in:
- `tests/test_verifiers.py` - Unit tests
- `tests/test_pipeline.py` - Roundtrip integration tests

## Implementation History

Comparison verifiers were added to ensure data integrity during extract → render → extract roundtrips.

**Key Files**:
- `cvextract/verifiers/roundtrip_verifier.py` - Implementation
- `cvextract/verifiers/base.py` - Base class

## Open Questions

1. **Fuzzy Matching**: Should we support approximate comparison (e.g., minor formatting differences)?
2. **Order Independence**: Should we support unordered list comparison for some fields?
3. **Diff Output**: Should we provide detailed diff output (like git diff)?

## File Paths

- Implementation: `cvextract/verifiers/roundtrip_verifier.py`
- Base Class: `cvextract/verifiers/base.py`
- Tests: `tests/test_verifiers.py`
- Documentation: `cvextract/verifiers/README.md`

## Related Documentation

- [Verification Architecture](../README.md)
- [Extracted Data Verifier](../extracted-data-verifier/README.md)
- [Schema Verifier](../schema-verifier/README.md)
- Module README: `cvextract/verifiers/README.md`
