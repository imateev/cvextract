# Default DOCX CV Extractor

## Overview

The default DOCX CV extractor is the default CV extraction implementation that directly parses Microsoft Word `.docx` files using WordprocessingML XML. It provides fast, deterministic, offline extraction without external API calls.

## Status

**Active** - Fully implemented and production-ready

## Description

This extractor reads `.docx` files by:
1. Opening the DOCX as a ZIP archive
2. Parsing `word/document.xml` for main body content (overview, experiences)
3. Parsing `word/header*.xml` for sidebar content (skills, certifications, etc.)
4. Extracting identity information from document headers
5. Detecting experience boundaries using date-range headings and Word styles
6. Collecting bullet points using Word list formatting and numbering properties

The extractor is optimized for DOCX files with a specific, predefined structure and does not handle arbitrary CV layouts.

## Entry Points

### Programmatic API

```python
from cvextract.cli_config import UserConfig
from cvextract.extractors import DocxCVExtractor
from cvextract.shared import StepName, UnitOfWork
from pathlib import Path
import json

extractor = DocxCVExtractor()
work = UnitOfWork(config=UserConfig(target_dir=Path("outputs")))
work.set_step_paths(
    StepName.Extract,
    input_path=Path("cv.docx"),
    output_path=Path("outputs/cv.json"),
)
extractor.extract(work)
output_path = work.get_step_output(StepName.Extract)
cv_data = json.loads(output_path.read_text(encoding="utf-8"))
```

### CLI Usage

```bash
# Default (default_docx_cv_extractor is used automatically)
python -m cvextract.cli --extract source=cv.docx --target output/

# Explicit specification
python -m cvextract.cli \
  --extract source=cv.docx name=default_docx_cv_extractor \
  --target output/
```

### Registry Access

```python
from cvextract.cli_config import UserConfig
from cvextract.extractors import get_extractor
from cvextract.shared import StepName, UnitOfWork
from pathlib import Path
import json

extractor = get_extractor("default_docx_cv_extractor")
work = UnitOfWork(config=UserConfig(target_dir=Path("outputs")))
work.set_step_paths(
    StepName.Extract,
    input_path=Path("cv.docx"),
    output_path=Path("outputs/cv.json"),
)
extractor.extract(work)
output_path = work.get_step_output(StepName.Extract)
cv_data = json.loads(output_path.read_text(encoding="utf-8"))
```

## Configuration

### CLI Parameters

- `source=<path>`: Path to DOCX file (required)
- `name=default_docx_cv_extractor`: Extractor name (optional, this is the default)
- `output=<path>`: Output JSON path (optional, defaults to `{target}/structured_data/`)

### Environment Variables

None required.

## Interfaces

### Input

- **File Format**: Microsoft Word `.docx` (Office Open XML)
- **Expected Structure**: 
  - Header with identity information and sidebar text boxes
  - Body with "OVERVIEW" and "PROFESSIONAL EXPERIENCE" sections
  - Experience entries with date-range headings
  - Bullet points using Word list formatting

### Output

JSON data conforming to `cvextract/contracts/cv_schema.json`:

```json
{
  "identity": {
    "title": "Job Title",
    "full_name": "Full Name",
    "first_name": "First",
    "last_name": "Last"
  },
  "sidebar": {
    "languages": ["Python", "Java"],
    "tools": ["Docker", "Kubernetes"],
    "certifications": ["CISSP"],
    "industries": ["Finance", "Healthcare"],
    "spoken_languages": ["English", "Spanish"],
    "academic_background": ["BS Computer Science"]
  },
  "overview": "Professional summary text...",
  "experiences": [
    {
      "heading": "Jan 2020 - Present | Senior Engineer",
      "description": "Job description...",
      "bullets": ["Achievement 1", "Achievement 2"],
      "environment": ["Python", "AWS"]
    }
  ]
}
```

## Dependencies

### Internal Dependencies

- `cvextract.extractors.base.CVExtractor` - Abstract base class
- `cvextract.extractors.sidebar_parser` - Sidebar content parsing
- `cvextract.extractors.body_parser` - Body content parsing
- `cvextract.extractors.docx_utils` - DOCX file utilities
- `cvextract.contracts.cv_schema.json` - Output data schema

### External Dependencies

- `lxml` - XML processing for WordprocessingML parsing

### Integration Points

- Registered in `cvextract/extractors/__init__.py` as `"default_docx_cv_extractor"`
- Used by `cvextract.pipeline_helpers.extract_cv_data()` as default (expects `UnitOfWork`)
- Used by `cvextract.cli_execute_pipeline.execute_pipeline()` for extraction stage

## Test Coverage

Tested in:
- `tests/test_docx_extractor.py` - Unit tests for DOCX extraction logic
- `tests/test_extractors.py` - Integration tests with sample CVs
- `tests/test_pipeline.py` - End-to-end pipeline tests

## Implementation History

### Initial Implementation

- **Commit**: Initial project setup (exact commit hash not available - predates current Git history)
- **Author**: Ivo Mateev
- **Description**: Original three-day implementation for CV migration project

### Refactoring to Pluggable Architecture

The extractor was refactored from inline code to a pluggable class-based architecture to support:
- Multiple extractor implementations
- Easy testing with mock extractors
- Runtime extractor selection

**Key Files**:
- `cvextract/extractors/base.py` - Abstract base class
- `cvextract/extractors/docx_extractor.py` - Main implementation
- `cvextract/extractors/extractor_registry.py` - Registry system

## Open Questions

1. **Format Support**: Should we add support for `.doc` (older Word format)?
2. **Structure Flexibility**: Should we make the expected document structure more flexible/configurable?
3. **Error Recovery**: Should we attempt partial extraction when structure is non-standard?

## Performance Characteristics

- **Speed**: Very fast (< 1 second per CV on typical hardware)
- **Offline**: No network calls required
- **Deterministic**: Same input always produces same output
- **Cost**: Free (no API costs)

## Limitations

- **DOCX Only**: Cannot process TXT, PDF, or other formats
- **Structure Dependent**: Requires specific document structure with expected sections and formatting
- **No AI**: Cannot interpret non-standard layouts or extract from unstructured text

## Use Cases

**Best For**:
- Batch processing of standardized DOCX CVs
- Offline/air-gapped environments
- High-volume processing where API costs are prohibitive
- Deterministic, reproducible extraction

**Not Suitable For**:
- Text files or PDFs
- CVs with non-standard layouts
- CVs without expected section headers
- Scanned documents (images)

## File Paths

- Implementation: `cvextract/extractors/docx_extractor.py`
- Sidebar Parser: `cvextract/extractors/sidebar_parser.py`
- Body Parser: `cvextract/extractors/body_parser.py`
- DOCX Utilities: `cvextract/extractors/docx_utils.py`
- Base Class: `cvextract/extractors/base.py`
- Tests: `tests/test_docx_extractor.py`, `tests/test_extractors.py`

## Related Documentation

- [Extractor Architecture](../README.md)
- [OpenAI Extractor](../openai-extractor/README.md) - Alternative for non-standard formats
- [Extractor Registry](../extractor-registry/README.md) - Registration system
- Module README: `cvextract/extractors/README.md`
