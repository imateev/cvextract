# Extraction Area

## Purpose

The extraction area provides a pluggable architecture for extracting structured CV data from various source formats (DOCX, TXT, etc.) into a standardized JSON format conforming to the CV schema.

## Features

- [Private Internal Extractor](private-internal-extractor/README.md) - Default DOCX parser using WordprocessingML XML
- [OpenAI Extractor](openai-extractor/README.md) - OpenAI-powered intelligent extraction for TXT/DOCX
- [Extractor Registry](extractor-registry/README.md) - Pluggable extractor registration and lookup system

## Architectural Notes

### Design Principles

1. **Pluggable Architecture**: All extractors implement the `CVExtractor` abstract base class
2. **Registry Pattern**: Extractors are registered by name and retrieved via factory functions
3. **Schema Conformance**: All extractors produce JSON data conforming to `cvextract/contracts/cv_schema.json`
4. **Interchangeability**: Extractors can be swapped at runtime via CLI or programmatic configuration

### Key Components

- **Base Interface**: `cvextract/extractors/base.py` - `CVExtractor` abstract base class
- **Registry**: `cvextract/extractors/extractor_registry.py` - Registration and lookup functions
- **Implementations**: 
  - `cvextract/extractors/docx_extractor.py` - Private internal DOCX parser
  - `cvextract/extractors/openai_extractor.py` - OpenAI-based extraction

### Data Flow

```
Source File (.docx, .txt)
    │
    v
[Extractor.extract(work: UnitOfWork)]
    │
    v
Structured JSON Data (Extract step output)
    │
    v
{
  "identity": {...},
  "sidebar": {...},
  "overview": "...",
  "experiences": [...]
}
```

### Integration Points

- **CLI**: `--extract source=<path> name=<extractor-name>`
- **Pipeline**: `cvextract.pipeline_helpers.extract_cv_data()` (expects `UnitOfWork`)
- **Verification**: Extracted data is validated by `ExtractedDataVerifier` and `CVSchemaVerifier`

## Dependencies

- **Internal**: `cvextract.contracts` (CV schema), `cvextract.shared` (prompt loading)
- **External**: 
  - `lxml` (XML parsing for private-internal-extractor)
  - `openai` (OpenAI API for openai-extractor)
  - `requests` (HTTP client for openai-extractor)

## File References

- Base: `cvextract/extractors/base.py`
- Registry: `cvextract/extractors/extractor_registry.py`
- DOCX Extractor: `cvextract/extractors/docx_extractor.py`
- OpenAI Extractor: `cvextract/extractors/openai_extractor.py`
- Public API: `cvextract/extractors/__init__.py`
- Documentation: `cvextract/extractors/README.md`
