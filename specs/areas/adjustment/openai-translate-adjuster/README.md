# Translate Adjuster

## Overview

The translate adjuster converts structured CV JSON into a target language while preserving schema, identifiers, and formatting structure.

## Status

**Active** - Fully implemented

## Description

The `OpenAITranslateAdjuster` class:
1. Accepts a target language (ISO code or name)
2. Translates content fields while preserving schema and keys
3. Preserves names, emails, URLs, tools, and programming languages
4. Keeps list structures and ordering intact
5. Validates translated output against the CV schema before returning

## Entry Points

### Programmatic API

```python
from pathlib import Path
from cvextract.adjusters import get_adjuster
from cvextract.cli_config import UserConfig, ExtractStage
from cvextract.shared import StepName, UnitOfWork

adjuster = get_adjuster("openai-translate", model="gpt-4o-mini")
work = UnitOfWork(
    config=UserConfig(target_dir=Path("out"), extract=ExtractStage(source=Path("cv.json"))),
)
work.set_step_paths(
    StepName.Adjust,
    input_path=Path("cv.json"),
    output_path=Path("cv_translated.json"),
)
adjusted_cv = adjuster.adjust(
    work,
    language="de"
)
```

### CLI Usage

```bash
export OPENAI_API_KEY="sk-proj-..."

python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-translate language=de \
  --render template=template.docx \
  --target output/
```

## Configuration

### Parameters

- **`language`** (required): Target language (ISO code or descriptive name)
- **`openai-model`** (optional): OpenAI model name, defaults to `gpt-4o-mini`
- **`temperature`** (optional): OpenAI temperature (default `0.0` for deterministic output)

### Environment Variables

- **`OPENAI_API_KEY`** (required): OpenAI API key
- **`OPENAI_MODEL`** (optional): Default model name

## Interfaces

### Input

- CV JSON data conforming to `cv_schema.json`

### Output

- Translated CV JSON with preserved schema and identifiers

## Dependencies

### Internal Dependencies

- `cvextract.adjusters.base.CVAdjuster` - Base class
- `cvextract.shared.format_prompt` - Prompt formatting
- `cvextract.contracts.cv_schema.json` - CV schema for validation
- `cvextract.adjusters.openai_utils` - Retry/backoff and schema access helpers

### External Dependencies

- `openai` (>= 1.0) - OpenAI API client

### Integration Points

- Registered as `"openai-translate"` in `cvextract/adjusters/__init__.py`
- Used by `cvextract.cli_execute_adjust.execute()` when `--adjust name=openai-translate`
- Can be chained with other adjusters

## Test Coverage

Tested in:
- `tests/test_translate_adjuster.py`
  - Golden fixture translation to a target language
  - Schema validation failure fallback
- `tests/test_adjusters.py` - Registry and list coverage
- `tests/test_cli_gather.py` - CLI list output

## Implementation History

The translate adjuster was added to enable multi-language CV workflows while keeping JSON structure stable for template rendering.

**Key Files**:
- `cvextract/adjusters/openai_translate_adjuster.py` - Implementation
- `cvextract/adjusters/prompts/adjuster_prompt_translate_cv.md` - Translation prompt

## Open Questions

1. **Glossary Support**: Should a user-provided glossary be supported for strict term preservation?
2. **Date/Unit Localization**: Should localized date formats and units be supported in a future version?

## File Paths

- Implementation: `cvextract/adjusters/openai_translate_adjuster.py`
- Prompt: `cvextract/adjusters/prompts/adjuster_prompt_translate_cv.md`
- Tests: `tests/test_translate_adjuster.py`
- Documentation: `cvextract/adjusters/README.md`

## Related Documentation

- [Adjustment Architecture](../README.md)
- [Named Adjusters](../named-adjusters/README.md)
- [Adjuster Chaining](../adjuster-chaining/README.md)
- Module README: `cvextract/adjusters/README.md`
