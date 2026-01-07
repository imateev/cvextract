# Contracts Area

## Purpose

The contracts area defines JSON schemas that serve as formal data contracts for CV data and company research data used throughout the application.

## Features

- [CV Schema](cv-schema/README.md) - JSON Schema for CV data structure
- [Research Schema](research-schema/README.md) - JSON Schema for company research data

## Architectural Notes

### Design Principles

1. **Formal Contracts**: JSON Schema provides machine-readable, enforceable contracts
2. **Single Source of Truth**: Schemas define structure for all modules
3. **Validation**: Used by verifiers to ensure data conformance
4. **Documentation**: Schemas serve as API documentation

### Key Components

- **CV Schema**: `cvextract/contracts/cv_schema.json` - Defines CV data structure
- **Research Schema**: `cvextract/contracts/research_schema.json` - Defines company research structure

### Schema Usage

```
Extractors → Produce data conforming to cv_schema.json
    ↓
Adjusters → Consume/produce data conforming to cv_schema.json
    ↓
Renderers → Consume data conforming to cv_schema.json

Company Research → Produces research data conforming to research_schema.json
```

### Integration Points

- **Extractors**: All extractors must produce data matching `cv_schema.json`
- **Adjusters**: Input/output must conform to `cv_schema.json`
- **Renderers**: Templates expect data matching `cv_schema.json`
- **Verifiers**: `CVSchemaVerifier` and `CompanyProfileVerifier` validate against schemas
- **Company Research**: Research cached using `research_schema.json`

## Dependencies

- **Internal**: Used by all major modules (extractors, adjusters, renderers, verifiers)
- **External**: None (verifiers use basic structure validation)

## File References

- CV Schema: `cvextract/contracts/cv_schema.json`
- Research Schema: `cvextract/contracts/research_schema.json`
- Documentation: `cvextract/contracts/README.md`
- Verifier: `cvextract/verifiers/default_cv_schema_verifier.py`
