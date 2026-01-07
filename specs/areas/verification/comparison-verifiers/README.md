# Roundtrip Verifiers

## Overview

Roundtrip verifiers check equivalence between two CV data structures, primarily used for roundtrip verification (extract → render → extract comparison).

## Status

**Active** - Core verification component

## Description

Two implementations:
1. **`RoundtripVerifier`**: Compares in-memory data structures
2. **`FileRoundtripVerifier`**: Loads and compares JSON files

Both check:
- Structural equivalence
- Field-by-field comparison
- Deep equality of nested structures
- List order and contents

## Entry Points

### RoundtripVerifier (In-Memory)

```python
from typing import Any, Dict
from cvextract.verifiers import get_verifier

verifier = get_verifier("roundtrip-verifier")
original_data: Dict[str, Any] = {...}
roundtrip_data: Dict[str, Any] = {...}
result = verifier.verify(data=original_data, target_data=roundtrip_data)

if result.ok:
    print("Data structures match!")
else:
    print(f"Differences: {result.errors}")
```

### FileRoundtripVerifier (Files)

```python
from cvextract.verifiers import get_verifier
from pathlib import Path

verifier = get_verifier("file-roundtrip-verifier")
source_file: Path = Path("original.json")
target_file: Path = Path("roundtrip.json")
result = verifier.verify(
    source_file=source_file,
    target_file=target_file
)
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

- **RoundtripVerifier**: `verify(data=..., target_data=...)`
- **FileRoundtripVerifier**: `verify(source_file=..., target_file=...)`

## Interfaces

### Input

- Two CV data structures (in-memory or file paths)

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
- `cvextract/verifiers/comparison_verifier.py` - Implementation
- `cvextract/verifiers/base.py` - Base class

## Open Questions

1. **Fuzzy Matching**: Should we support approximate comparison (e.g., minor formatting differences)?
2. **Order Independence**: Should we support unordered list comparison for some fields?
3. **Diff Output**: Should we provide detailed diff output (like git diff)?

## File Paths

- Implementation: `cvextract/verifiers/comparison_verifier.py`
- Base Class: `cvextract/verifiers/base.py`
- Tests: `tests/test_verifiers.py`
- Documentation: `cvextract/verifiers/README.md`

## Related Documentation

- [Verification Architecture](../README.md)
- [Extracted Data Verifier](../extracted-data-verifier/README.md)
- [Schema Verifier](../schema-verifier/README.md)
- Module README: `cvextract/verifiers/README.md`
