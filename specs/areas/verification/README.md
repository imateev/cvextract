# Verification Area

## Purpose

The verification area provides data validation and quality checking capabilities for extracted and rendered CV data.

## Features

- [Extracted Data Verifier](extracted-data-verifier/README.md) - Validates completeness and structure of extracted data
- [Comparison Verifiers](comparison-verifiers/README.md) - Compares data structures for roundtrip verification
- [Schema Verifier](schema-verifier/README.md) - Validates CV data against JSON schema
- [Verifier Registry](verifier-registry/README.md) - Pluggable verifier registration and lookup system

## Architectural Notes

### Design Principles

1. **Pluggable Architecture**: All verifiers implement the `CVVerifier` abstract base class
2. **Registry-Based**: Verifiers are registered and accessed via a central registry
3. **Result Objects**: Verifiers return `VerificationResult` with ok/errors/warnings
4. **Composable**: Multiple verifiers can be applied to the same data
5. **Fail-Safe**: Verifiers never modify data, only report issues

### Key Components

- **Base Interface**: `cvextract/verifiers/base.py` - `CVVerifier` abstract base class
- **Registry**: `cvextract/verifiers/verifier_registry.py` - Central verifier registry
- **Result Type**: `cvextract/shared.py` - `VerificationResult` dataclass
- **Implementations**:
  - `cvextract/verifiers/data_verifier.py` - Completeness checks (registered as `data-verifier`)
  - `cvextract/verifiers/schema_verifier.py` - JSON schema validation (registered as `schema-verifier`)
  - `cvextract/verifiers/comparison_verifier.py` - Data comparison (registered as `roundtrip-verifier`, `file-roundtrip-verifier`)

### Data Flow

```
CV JSON Data
    │
    v
[get_verifier(name) -> Verifier Instance]
    │
    v
[Verifier.verify(data, **kwargs)]
    │
    v
VerificationResult(ok, errors, warnings)
```

### Registry Usage

The verifier registry provides a consistent API for managing verifiers:

```python
from cvextract.verifiers import get_verifier, list_verifiers, register_verifier

# List available verifiers
verifiers = list_verifiers()  # Returns [{'name': '...', 'description': '...'}, ...]

# Get a verifier instance
verifier = get_verifier('data-verifier')
result = verifier.verify(cv_data)

# Register custom verifiers
register_verifier('my-custom-verifier', MyCustomVerifierClass)
```

### Integration Points

- **Pipeline**: Used in `cvextract.pipeline` for extraction and roundtrip validation
- **CLI**: Results logged and affect exit codes (--strict mode)

## Dependencies

- **Internal**: `cvextract.shared` (VerificationResult), `cvextract.contracts` (schemas)
- **External**: `jsonschema` (schema validation)

## File References

- Base: `cvextract/verifiers/base.py`
- Registry: `cvextract/verifiers/verifier_registry.py`
- Data Verifier: `cvextract/verifiers/data_verifier.py`
- Schema Verifier: `cvextract/verifiers/schema_verifier.py`
- Comparison Verifier: `cvextract/verifiers/comparison_verifier.py`
- Public API: `cvextract/verifiers/__init__.py`
- Documentation: `cvextract/verifiers/README.md`
