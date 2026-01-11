# Named Flags

## Overview

Named flags provide modern `key=value` parameter syntax for all CLI parameters, making commands self-documenting and reducing ambiguity.

## Status

**Active** - Core CLI syntax

## Description

All CLI parameters use explicit naming:
1. **Self-Documenting**: Each parameter clearly states what it controls
2. **No Positional Args**: Order doesn't matter (within a flag's scope)
3. **Values with Spaces**: Proper handling of paths and text with spaces
4. **Boolean Flags**: Flags without values (e.g., `skip-verify`)

## Entry Points

### CLI Usage

```bash
# Extract parameters
python -m cvextract.cli \
  --extract source=/path/to/cv.docx name=openai-extractor output=custom.json \
  --target output/ \
  --verbosity debug

# Adjust parameters
python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com openai-model=gpt-4 \
  --target output/ \
  --verbosity debug

# Apply parameters
python -m cvextract.cli \
  --render template=/path/to/template.docx data=cv.json output=result.docx \
  --target output/ \
  --verbosity debug

# Parallel parameters
python -m cvextract.cli \
  --parallel source=/path/to/cvs n=10 \
  --extract \
  --target output/ \
  --verbosity debug
```

## Configuration

### Parameter Format

- **Key-Value**: `key=value` - Space-separated pairs
- **Boolean**: `flag` - No value means true/present
- **Paths with Spaces**: Automatically handled by shell quoting
  - `source="/path with spaces/file.docx"`
  - `source=/path\ with\ spaces/file.docx`

### Stage Parameters

**Extract**:
- `source=<path>` - Input file/directory
- `name=<extractor[,extractor,...]>` - Extractor name(s) (tried in order)
- `output=<path>` - Output JSON path

**Adjust**:
- `name=<adjuster>` - Adjuster name (required)
- `data=<path>` - Input JSON (when not chained)
- `output=<path>` - Output JSON path
- `customer-url=<url>` - For company research
- `job-url=<url>` - For job-specific
- `job-description=<text>` - For job-specific
- `language=<target>` - For translation
- `openai-model=<model>` - OpenAI model override

**Apply**:
- `template=<path>` - Template file (required)
- `data=<path>` - Input JSON (when not chained)
- `output=<path>` - Output DOCX path

**Parallel**:
- `source=<dir>` - Input directory
- `n=<count>` - Worker count

## Interfaces

### Parsing Logic

```python
# In cli_gather.py
def _parse_key_value_args(args):
    """Parse space-separated key=value arguments."""
    params = {}
    for arg in args:
        if '=' in arg:
            key, value = arg.split('=', 1)
            params[key] = value
        else:
            # Boolean flag
            params[arg] = True
    return params
```

### Validation

```python
# Required parameters checked
if 'source' not in extract_params:
    raise ValueError("--extract requires source= parameter")

if 'name' not in adjust_params:
    raise ValueError("--adjust requires name= parameter")
```

## Dependencies

### Internal Dependencies

- `cvextract.cli_gather` - Parameter parsing
- `cvextract.cli_config` - Configuration objects

### Integration Points

- All CLI stages use this syntax
- Consistent across extract, adjust, render, parallel

## Test Coverage

Tested in:
- `tests/test_cli.py` - Parameter parsing tests
- `tests/test_cli_gather.py` - Validation tests

## Implementation History

Named flags replaced earlier positional argument syntax to improve clarity and maintainability.

**Key Files**:
- `cvextract/cli_gather.py` - Parsing implementation
- `cvextract/cli.py` - Argument definitions

## Examples

### Basic Parameters

```bash
# Single values
--extract source=cv.docx
--adjust name=openai-company-research
--render template=template.docx

# Multiple parameters
--extract source=cv.docx name=openai-extractor output=data.json
--adjust name=openai-job-specific job-url=https://example.com/job/123 openai-model=gpt-4
--adjust name=openai-translate language=de openai-model=gpt-4o-mini
```

### Boolean Flags

```bash
# skip-verify flag (no value)
--adjust name=openai-company-research customer-url=https://example.com skip-verify

# Global boolean flags
--debug
```

### Paths with Spaces

```bash
# Method 1: Quotes
--extract source="/my documents/cv folder/engineer.docx"

# Method 2: Backslash escaping
--extract source=/my\ documents/cv\ folder/engineer.docx

# Template with spaces
--render template="/templates/Modern CV Template.docx"
```

### Complex Example

```bash
export OPENAI_API_KEY="sk-proj-..."

python -m cvextract.cli \
  --extract source="/data/cvs/2025/Q1" name=openai-extractor output=extracts/ \
  --adjust name=openai-company-research customer-url=https://target-company.com openai-model=gpt-4 \
  --adjust name=openai-job-specific job-url=https://target-company.com/careers/job/456 \
  --render template="/templates/Company Template.docx" output=results/ \
  --target /output \
  --log-file /output/processing.log \
  --debug
```

## File Paths

- Implementation: `cvextract/cli_gather.py` (functions: `_parse_key_value_args`, `_parse_extract_spec`, etc.)
- Tests: `tests/test_cli.py`
- Documentation: Main README.md "Parameter Syntax" section

## Related Documentation

- [CLI Architecture](../README.md)
- [Stage-Based Interface](../stage-based-interface/README.md)
- Main README: "Parameter Syntax" and all examples sections
