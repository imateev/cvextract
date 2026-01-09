# OpenAI Extractor

## Overview

The OpenAI extractor uses OpenAI's GPT models to intelligently extract structured CV data from various text formats including TXT and DOCX files. It can handle non-standard layouts that the private internal extractor cannot process.

## Status

**Active** - Fully implemented and production-ready

## Description

This extractor leverages OpenAI's GPT models with production-grade reliability features to:
1. Read text content from TXT or DOCX files
2. Upload documents to OpenAI's file storage
3. Create an Assistant with specialized CV extraction instructions
4. Send the document to the Assistant and poll for completion
5. Extract and parse the structured response
6. Validate against the standard CV schema

### Architecture Highlights

**Retry & Backoff Logic** _(Production-Ready)_:
- Centralized retry wrapper with configurable max attempts (default: 8)
- Exponential backoff with full jitter: `delay = random() × min(base × 2^attempt × multiplier, max_delay)`
- Transient error detection: 429 (rate limit), 5xx, timeouts, SSL/TLS issues
- Retry-After header parsing and honor
- Write operations use higher multiplier (1.6×) for longer backoff
- Deterministic mode for testing (reproducible retry behavior)

**Adaptive Polling** _(Reduces 429 Errors)_:
- Schedule-based polling: [1.0, 1.0, 2.0, 3.0, 5.0, 8.0, 10.0] seconds
- Hard timeout on runs (default: 180 seconds)
- Prevents excessive polling on long-running operations

**Resource Management**:
- Automatic cleanup of temporary resources (assistants, files)
- Best-effort deletion with graceful error handling
- Finally blocks ensure cleanup even on exceptions

The extractor is format-agnostic and can extract from any text-based source, making it ideal for non-standard CV layouts.

## Entry Points

### Programmatic API

```python
from cvextract.cli_config import UserConfig
from cvextract.extractors import OpenAICVExtractor
from cvextract.shared import StepName, UnitOfWork
from pathlib import Path
import json

extractor = OpenAICVExtractor()
work = UnitOfWork(config=UserConfig(target_dir=Path("outputs")))
work.set_step_paths(
    StepName.Extract,
    input_path=Path("cv.txt"),
    output_path=Path("outputs/cv.json"),
)
extractor.extract(work)
output_path = work.get_step_output(StepName.Extract)
cv_data = json.loads(output_path.read_text(encoding="utf-8"))
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
from cvextract.cli_config import UserConfig
from cvextract.extractors import get_extractor
from cvextract.shared import StepName, UnitOfWork
from pathlib import Path
import json

extractor = get_extractor("openai-extractor")
work = UnitOfWork(config=UserConfig(target_dir=Path("outputs")))
work.set_step_paths(
    StepName.Extract,
    input_path=Path("cv.txt"),
    output_path=Path("outputs/cv.json"),
)
extractor.extract(work)
output_path = work.get_step_output(StepName.Extract)
cv_data = json.loads(output_path.read_text(encoding="utf-8"))
```

## Configuration

### CLI Parameters

- `source=<path>`: Path to TXT or DOCX file (required)
- `name=openai-extractor`: Extractor name (required to use this extractor)
- `output=<path>`: Output JSON path (optional, defaults to `{target}/structured_data/`)

### Environment Variables

- **`OPENAI_API_KEY`** (required): OpenAI API key for authentication
- **`OPENAI_MODEL`** (optional): Model name, defaults to `gpt-4o`

### Programmatic Configuration

```python
from cvextract.cli_config import UserConfig
from cvextract.extractors import OpenAICVExtractor
from cvextract.extractors.openai_extractor import _RetryConfig
from cvextract.shared import StepName, UnitOfWork
from pathlib import Path
import json

# Default configuration
extractor = OpenAICVExtractor()
work = UnitOfWork(config=UserConfig(target_dir=Path("outputs")))
work.set_step_paths(
    StepName.Extract,
    input_path=Path("cv.txt"),
    output_path=Path("outputs/cv.json"),
)
extractor.extract(work)
output_path = work.get_step_output(StepName.Extract)
cv_data = json.loads(output_path.read_text(encoding="utf-8"))

# Custom model and timeout
extractor = OpenAICVExtractor(
    model='gpt-4-turbo',
    run_timeout_s=300.0  # 5-minute timeout for long documents
)

# Custom retry behavior
custom_retry = _RetryConfig(
    max_attempts=10,
    base_delay_s=1.0,
    max_delay_s=30.0,
    write_multiplier=2.0,  # Extra backoff for write operations
    deterministic=True     # For testing
)
extractor = OpenAICVExtractor(retry_config=custom_retry)
```

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

- `openai` (>= 1.0) - OpenAI Python client library for API access

### Integration Points

- Registered in `cvextract/extractors/__init__.py` as `"openai-extractor"`
- Used by `cvextract.cli_execute_pipeline.execute_pipeline()` when `name=openai-extractor` specified
- Can be used in parallel processing mode via `cvextract.cli_execute_parallel`

## Test Coverage

**Comprehensive test suite** (37 tests, 100% pass rate):

- **Initialization** (5 tests): Model selection, retry config, timeout settings
- **File Validation** (3 tests): Missing files, directories, file type acceptance
- **Retry Mechanisms** (10 tests):
  - Transient error detection (429, 5xx, timeouts)
  - Retry-After header parsing
  - Exponential backoff calculation
  - Max attempts exhaustion
  - Non-transient error handling
- **OpenAI Operations** (7 tests): File upload, assistant/thread/message/run creation, cleanup
- **Polling** (3 tests): Immediate completion, multiple iterations, timeout handling
- **Message Extraction** (3 tests): Text extraction, data handling, message filtering
- **Parsing & Validation** (5 tests): Code fence handling, JSON parsing, schema validation
- **Integration** (1 test): Full schema structure validation

Tested in:
- `tests/test_openai_extractor.py` - 37 unit tests with mocked OpenAI responses
- `tests/test_extractors.py` - Integration tests
- Manual testing with actual OpenAI API calls

## Implementation History

### Initial Implementation

The OpenAI extractor was added to support text files and non-standard DOCX formats that the private internal extractor cannot handle.

### Recent Enhancements (Production Hardening)

**v2.0 - Retry & Reliability Architecture** _(Latest)_:
- Implemented centralized `_call_with_retry()` wrapper for all OpenAI operations
- Added exponential backoff with full jitter to reduce cascading failures
- Implemented adaptive polling schedule to prevent 429 rate limit errors
- Added Retry-After header parsing and honor
- Implemented hard timeout on run polling (default 180 seconds)
- Enhanced error classification to distinguish transient vs. permanent failures
- Improved resource cleanup with best-effort deletion
- Added comprehensive test coverage (37 tests) for all retry/backoff scenarios
- Made retry behavior configurable via `_RetryConfig` dataclass
- Added testability hooks (`_sleep`, `_time` injection) for deterministic testing

**Key Files**:
- `cvextract/extractors/openai_extractor.py` - Main implementation (488 lines)
- `cvextract/extractors/base.py` - Shared base class
- `cvextract/extractors/__init__.py` - Registry integration
- `tests/test_openai_extractor.py` - Comprehensive test suite (37 tests)

## Open Questions

1. **PDF Support**: Should we add PyPDF2/pdfplumber for PDF extraction?
2. **PPTX Support**: Should we support PowerPoint resume formats?
3. **Cost Optimization**: Should we implement chunking for very long CVs?
4. **Fallback**: Should we fall back to private-internal-extractor on API failures for DOCX?

## Performance Characteristics

- **Speed**: ~5-10 seconds per CV (depends on OpenAI API response time)
- **Reliability**: Production-grade with exponential backoff and adaptive polling
- **Retry Behavior**: Automatic retries (8 attempts default) with exponential backoff
- **Rate Limiting**: Handles 429 with Retry-After header parsing
- **Timeout**: Hard timeout of 180 seconds on individual run operations (configurable)
- **Online**: Requires internet connection and OpenAI API access
- **Non-Deterministic**: Same input may produce slightly different outputs
- **Cost**: Costs apply based on OpenAI API usage (typically $0.01-0.05 per CV)
- **Resource Management**: Automatic cleanup of temporary assistants and files

## Limitations

- **API Dependency**: Requires valid OpenAI API key and internet access
- **Cost**: API usage costs apply (automatic retries may increase costs on failures)
- **Timeout**: Hard timeout of 180 seconds (may fail on very long documents)
- **Availability**: Dependent on OpenAI service availability
- **Non-Deterministic**: Output may vary slightly across runs due to GPT nature

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
