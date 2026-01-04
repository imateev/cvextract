# Stage-Based Interface

## Overview

The stage-based interface provides explicit CLI flags (`--extract`, `--adjust`, `--apply`) for each pipeline operation, making workflows clear and composable.

## Status

**Active** - Core CLI design

## Description

Key characteristics:
1. **Explicit Stages**: Each operation has its own flag
2. **Auto-Chaining**: Output of one stage becomes input to next
3. **Selective Execution**: Run any combination of stages
4. **Clear Semantics**: Each flag's purpose is immediately obvious

## Entry Points

### CLI Usage

```bash
# Extract only
python -m cvextract.cli --extract source=cv.docx --target output/

# Extract + Apply
python -m cvextract.cli \
  --extract source=cv.docx \
  --apply template=template.docx \
  --target output/

# Extract + Adjust + Apply
python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com \
  --apply template=template.docx \
  --target output/

# Apply only (from existing JSON)
python -m cvextract.cli \
  --apply template=template.docx data=cv.json \
  --target output/
```

## Configuration

### Stage Flags

- **`--extract`**: Extract CV data from source file
  - Required params: `source=<path>`
  - Optional params: `name=<extractor>`, `output=<path>`

- **`--adjust`**: Adjust CV data (can be repeated for chaining)
  - Required params: `name=<adjuster>`, adjuster-specific params
  - Optional params: `data=<path>` (when not chained), `output=<path>`, `openai-model=<model>`, `dry-run`

- **`--apply`**: Apply CV data to template
  - Required params: `template=<path>`
  - Optional params: `data=<path>` (when not chained), `output=<path>`

### Global Options

- **`--target <dir>`**: Output directory (required)
- **`--list {extractors,adjusters,renderers}`**: List available components
- **`-v, --verbose`**: Increase output verbosity (repeatable: -v for normal, -vv for verbose)
- **`--log-file <path>`**: Log file path

## Interfaces

### Auto-Chaining Behavior

When stages are chained:
- Extract → Adjust: Extracted JSON auto-passed to adjust
- Adjust → Apply: Adjusted JSON auto-passed to apply  
- Extract → Apply: Extracted JSON auto-passed to apply (skipping adjust)

The `data=` parameter is only needed when running stages standalone.

## Dependencies

### Internal Dependencies

- `cvextract.cli_gather` - Argument parsing
- `cvextract.cli_execute` - Stage execution
- `cvextract.cli_config.UserConfig` - Configuration storage

### Integration Points

- Implemented in `cvextract/cli.py` - Argument parser setup
- Validated in `cvextract/cli_gather.py` - Stage validation
- Executed in `cvextract/cli_execute.py` - Stage orchestration

## Implementation History

The stage-based interface was designed to make the pipeline explicit and composable, replacing earlier monolithic commands.

**Key Files**:
- `cvextract/cli.py` - Argument definitions
- `cvextract/cli_gather.py` - Stage parsing
- `cvextract/cli_execute.py` - Stage execution

## File Paths

- Implementation: `cvextract/cli.py`, `cvextract/cli_gather.py`, `cvextract/cli_execute.py`
- Tests: `tests/test_cli.py`
- Documentation: Main README.md "CLI Interface" section

## Related Documentation

- [CLI Architecture](../README.md)
- [Named Flags](../named-flags/README.md)
- [Batch Processing](../batch-processing/README.md)
- Main README: "CLI Interface" section
