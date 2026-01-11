# Translation Example

## Overview

The translation example demonstrates how to translate extracted CV JSON into a target language and render a DOCX template.

## Status

**Active** - Example documentation

## Description

The example shows a full pipeline:
1. Extract from a DOCX CV
2. Translate structured JSON using the `openai-translate` adjuster
3. Render with an existing DOCX template

## Entry Points

### Example File

- `examples/translation/README.md`

## Dependencies

- Requires `OPENAI_API_KEY` for the translation adjuster
- Uses sample CVs from `examples/cvs/`
- Uses templates from `examples/templates/`

## File References

- Example: `examples/translation/README.md`
- Sample CVs: `examples/cvs/*.docx`
- Templates: `examples/templates/*.docx`

## Related Documentation

- [Examples Area](../README.md)
- [Translate Adjuster](../../adjustment/openai-translate-adjuster/README.md)
