# Verification Area

## Purpose

The verification area provides data validation and quality checking capabilities for extracted and rendered CV data.

## Features

- [Extracted Data Verifier](extracted-data-verifier/README.md) - Validates completeness and structure of extracted data
- [Roundtrip Verifier](comparison-verifiers/README.md) - Compares data structures for roundtrip verification
- [Schema Verifier](schema-verifier/README.md) - Validates CV data against JSON schema
- [Company Profile Verifier](company-profile-verifier/README.md) - Validates company research data against JSON schema
- [Verifier Registry](verifier-registry/README.md) - Pluggable verifier registration and lookup system

## Architectural Notes

### Design Principles

1. **Pluggable Architecture**: All verifiers implement the `CVVerifier` abstract base class
2. **Result Objects**: Verifiers return `VerificationResult` with ok/errors/warnings
3. **Composable**: Multiple verifiers can be applied to the same data
4. **Fail-Safe**: Verifiers never modify data, only report issues

### Key Components

- **Base Interface**: `cvextract/verifiers/base.py` - `CVVerifier` abstract base class
- **Result Type**: `cvextract/shared.py` - `VerificationResult` dataclass
- **Implementations**:
  - `cvextract/verifiers/default_expected_cv_data_verifier.py` - Completeness validation (registered as `private-internal-verifier`)
  - `cvextract/verifiers/default_cv_schema_verifier.py` - CV JSON schema validation (registered as `cv-schema-verifier`)
  - `cvextract/verifiers/default_company_research_verifier.py` - Company profile schema validation (registered as `company-profile-verifier`)
  - `cvextract/verifiers/roundtrip_verifier.py` - Data comparison (registered as `roundtrip-verifier`)

### Data Flow

```
CV JSON Data
    │
    v
[Verifier.verify(data=data, **kwargs)]
    │
    v
VerificationResult(ok, errors, warnings)
```

### Integration Points

- **Pipeline**: Used in `cvextract.pipeline` for extraction and roundtrip validation
- **CLI**: Results logged and affect exit codes

## Dependencies

- **Internal**: `cvextract.shared` (VerificationResult), `cvextract.contracts` (schemas)
- **External**: `jsonschema` (schema validation)

## File References

- Base: `cvextract/verifiers/base.py`
- Data Verifier: `cvextract/verifiers/default_expected_cv_data_verifier.py`
- Schema Verifier: `cvextract/verifiers/default_cv_schema_verifier.py`
- Roundtrip Verifier: `cvextract/verifiers/roundtrip_verifier.py`
- Public API: `cvextract/verifiers/__init__.py`
- Documentation: `cvextract/verifiers/README.md`
