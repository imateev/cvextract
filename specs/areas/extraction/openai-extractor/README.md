# OpenAI Extractor

## Overview

The OpenAI extractor uses OpenAI's GPT models to intelligently extract structured CV data from various text formats including TXT and DOCX files. It can handle non-standard layouts that the private internal extractor cannot process.

## Status

**Active** - Fully implemented and production-ready

## Description

This extractor leverages OpenAI's language understanding capabilities to:
1. Read text content from TXT or DOCX files
2. Send the content to OpenAI API with structured extraction instructions
3. Parse the AI response into the standard CV schema
4. Validate and return structured JSON data

The extractor is format-agnostic and can extract from any text-based source, making it ideal for non-standard CV layouts.

## Entry Points

### Programmatic API

```python
from cvextract.extractors import OpenAICVExtractor
from pathlib import Path

extractor = OpenAICVExtractor()
cv_data = extractor.extract(Path("cv.txt"))
```

### CLI Usage

```bash
# Extract from text file
export OPENAI_API_KEY="sk-proj-..."
python -m cvextract.cli \
  --extract source=cv.txt name=openai-extractor \
  --target output/

# Extract from non-standard DOCX
python -m cvextract.cli \
  --extract source=unusual-cv.docx name=openai-extractor \
  --target output/
```

### Registry Access

```python
from cvextract.extractors import get_extractor

extractor = get_extractor("openai-extractor")
cv_data = extractor.extract(Path("cv.txt"))
```

## Configuration

### CLI Parameters

- `source=<path>`: Path to TXT or DOCX file (required)
- `name=openai-extractor`: Extractor name (required to use this extractor)
- `output=<path>`: Output JSON path (optional, defaults to `{target}/structured_data/`)

### Environment Variables

- **`OPENAI_API_KEY`** (required): OpenAI API key for authentication
- **`OPENAI_MODEL`** (optional): Model name, defaults to `gpt-4o-mini`

## Interfaces

### Input

- **File Formats**: 
  - Plain text (`.txt`)
  - Microsoft Word (`.docx`)
  - Future: PDF, PPTX (with additional libraries)
- **Structure**: Any text-based CV format (no specific structure required)

### Output

JSON data conforming to `cvextract/contracts/cv_schema.json` (same schema as private-internal-extractor).

## Dependencies

### Internal Dependencies

- `cvextract.extractors.base.CVExtractor` - Abstract base class
- `cvextract.contracts.cv_schema.json` - Output data schema

### External Dependencies

- `openai` (>= 1.0) - OpenAI Python client library
- `python-docx` - For reading DOCX text content

### Integration Points

- Registered in `cvextract/extractors/__init__.py` as `"openai-extractor"`
- Used by `cvextract.cli_execute.execute_pipeline()` when `name=openai-extractor` specified
- Can be used in parallel processing mode via `cvextract.cli_parallel`

## Test Coverage

Tested in:
- `tests/test_openai_extractor.py` - Unit tests with mocked OpenAI responses
- `tests/test_extractors.py` - Integration tests
- Manual testing with actual OpenAI API calls

## Implementation History

### Initial Implementation

The OpenAI extractor was added to support text files and non-standard DOCX formats that the private internal extractor cannot handle.

**Key Files**:
- `cvextract/extractors/openai_extractor.py` - Main implementation
- `cvextract/extractors/base.py` - Shared base class
- `cvextract/extractors/__init__.py` - Registry integration

## Open Questions

1. **PDF Support**: Should we add PyPDF2/pdfplumber for PDF extraction?
2. **PPTX Support**: Should we support PowerPoint resume formats?
3. **Cost Optimization**: Should we implement chunking for very long CVs?
4. **Fallback**: Should we fall back to private-internal-extractor on API failures for DOCX?

## Performance Characteristics

- **Speed**: Slower than private-internal-extractor (depends on OpenAI API response time)
- **Online**: Requires internet connection and OpenAI API access
- **Non-Deterministic**: Same input may produce slightly different outputs
- **Cost**: Costs apply based on OpenAI API usage (typically $0.01-0.05 per CV)

## Limitations

- **API Dependency**: Requires valid OpenAI API key and internet access
- **Cost**: API usage costs apply
- **Rate Limits**: Subject to OpenAI rate limiting
- **Availability**: Dependent on OpenAI service availability

## Use Cases

**Best For**:
- Text (.txt) files
- Non-standard DOCX layouts
- CVs without expected section structure
- One-off extractions where flexibility is needed

**Not Suitable For**:
- Offline/air-gapped environments
- High-volume batch processing (due to cost and speed)
- When deterministic output is required
- When API dependencies are not acceptable

## File Paths

- Implementation: `cvextract/extractors/openai_extractor.py`
- Base Class: `cvextract/extractors/base.py`
- Tests: `tests/test_openai_extractor.py`

## Related Documentation

- [Extractor Architecture](../README.md)
- [Private Internal Extractor](../private-internal-extractor/README.md) - Default DOCX parser
- [Extractor Registry](../extractor-registry/README.md) - Registration system
- Module README: `cvextract/extractors/README.md`
- Main README: Section on "Pluggable Extractors"
