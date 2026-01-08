# Verifier Registry

## Overview

The Verifier Registry provides a centralized system for managing and accessing CV verifiers. It mirrors the architecture of the Extractor Registry, enabling consistent, registry-based access to verification implementations.

## Status

**Active** - Fully implemented and integrated into the verifier subsystem.

## Purpose

Provide a pluggable architecture for verifier registration and lookup, making it easy to:
- Add new verifiers without modifying core code
- List available verifiers programmatically
- Instantiate verifiers by name
- Extend the verification system with custom implementations

## Architecture

### Design Principles

1. **Registry-Based Access**: All verifiers are registered and accessed through a central registry
2. **Consistent API**: Mirrors the extractor registry API for familiarity
3. **Pluggable**: New verifiers can be added at runtime via `register_verifier()`
4. **Type-Safe**: All registered verifiers must implement the `CVVerifier` interface

### Key Components

- **Registry Module**: `cvextract/verifiers/verifier_registry.py`
- **Registration**: `register_verifier(name, verifier_class)`
- **Lookup**: `get_verifier(name, **kwargs)`
- **Discovery**: `list_verifiers()`
- **Cleanup**: `unregister_verifier(name)`

## Usage

### Listing Available Verifiers

```python
from cvextract.verifiers import list_verifiers

verifiers = list_verifiers()
for v in verifiers:
    print(f"{v['name']}: {v['description']}")
```

Example output:
```
company-profile-verifier: Verifier that validates company profile data against research_schema.json.
cv-schema-verifier: Verifier that validates CV data against cv_schema.json.
private-internal-verifier: Verifier for extracted CV data completeness and validity.
roundtrip-verifier: Verifier for comparing two CV data structures.
```

### Getting a Verifier Instance

```python
from typing import Any, Dict
from cvextract.verifiers import get_verifier

cv_data: Dict[str, Any] = {...}

# Get a verifier by name
verifier = get_verifier('private-internal-verifier')
result = verifier.verify(data=cv_data)

# Pass constructor arguments
verifier = get_verifier('cv-schema-verifier', schema_path=custom_schema_path)
result = verifier.verify(data=cv_data)
```

### Registering Custom Verifiers

```python
from cvextract.verifiers import CVVerifier, register_verifier
from cvextract.shared import VerificationResult

class CustomVerifier(CVVerifier):
    """My custom CV verifier."""
    
    def verify(self, **kwargs):
        # Custom verification logic
        return VerificationResult(errors=[], warnings=[])

# Register the custom verifier
register_verifier('my-custom-verifier', CustomVerifier)

# Now it can be used like any built-in verifier
verifier = get_verifier('my-custom-verifier')
```

## Built-in Verifiers

The following verifiers are registered by default:

| Name | Class | Description |
|------|-------|-------------|
| `private-internal-verifier` | `ExtractedDataVerifier` | Validates completeness and structure of extracted data |
| `roundtrip-verifier` | `RoundtripVerifier` | Compares two CV data structures |
| `cv-schema-verifier` | `CVSchemaVerifier` | Validates CV data against cv_schema.json |
| `company-profile-verifier` | `CompanyProfileVerifier` | Validates company research data against research_schema.json |

## Implementation Details

### Registry Structure

```python
_VERIFIER_REGISTRY: Dict[str, Type[CVVerifier]] = {}
```

The registry is a simple dictionary mapping verifier names to verifier classes.

### Registration Flow

1. Verifier classes are defined in their respective modules
2. `cvextract/verifiers/__init__.py` imports all verifier classes
3. `register_verifier()` is called for each built-in verifier
4. The registry is populated and ready for use

### API Consistency

The verifier registry API exactly mirrors the extractor registry:

| Verifier Registry | Extractor Registry |
|-------------------|-------------------|
| `register_verifier(name, verifier_class)` | `register_extractor(name, extractor_class)` |
| `get_verifier(name, **kwargs)` | `get_extractor(name, **kwargs)` |
| `list_verifiers()` | `list_extractors()` |
| `unregister_verifier(name)` | `unregister_extractor(name)` |

## Integration Points

### With Verifiers Module

All verifier registration happens in `cvextract/verifiers/__init__.py`:

```python
from .verifier_registry import register_verifier

# Register built-in verifiers
register_verifier("private-internal-verifier", ExtractedDataVerifier)
register_verifier("roundtrip-verifier", RoundtripVerifier)
register_verifier("cv-schema-verifier", CVSchemaVerifier)
register_verifier("company-profile-verifier", CompanyProfileVerifier)
```

### With Public API

The registry functions are exported in `__all__` for public use:

```python
__all__ = [
    "CVVerifier",
    "ExtractedDataVerifier",
    "RoundtripVerifier",
    "CVSchemaVerifier",
    "register_verifier",
    "get_verifier",
    "list_verifiers",
]
```

### Backward Compatibility

Direct instantiation of verifier classes remains supported:

```python
# Registry-based (recommended)
verifier = get_verifier('private-internal-verifier')

# Direct instantiation (still works)
from cvextract.verifiers import ExtractedDataVerifier
verifier = ExtractedDataVerifier()
```

## Testing

Tests are provided in `tests/test_verifier_registry.py`:

- Registration and retrieval of built-in verifiers
- Unknown verifier handling
- Custom verifier registration
- Parameter passing to constructors
- List sorting and description extraction

## File References

- Registry Implementation: `cvextract/verifiers/verifier_registry.py`
- Public API: `cvextract/verifiers/__init__.py`
- Tests: `tests/test_verifier_registry.py`
- Documentation: `cvextract/verifiers/README.md`

## Related Features

- [Extracted Data Verifier](../extracted-data-verifier/README.md)
- [Roundtrip Verifier](../comparison-verifiers/README.md)
- [Schema Verifier](../schema-verifier/README.md)
- [Company Profile Verifier](../company-profile-verifier/README.md)
- [Extractor Registry](../../extraction/extractor-registry/README.md)

## Design Rationale

### Why Mirror Extractor Registry?

The verifier registry follows the same design as the extractor registry to:
1. Provide a consistent developer experience across the codebase
2. Reduce cognitive load when working with multiple registry systems
3. Ensure maintainability and predictability
4. Enable future CLI/API extensions that work uniformly across subsystems

### Future Extensions

The registry architecture enables:
- Dynamic verifier discovery for CLI commands
- Plugin-based verifier loading
- Configuration-driven verifier selection
- Automated verifier chaining and composition
