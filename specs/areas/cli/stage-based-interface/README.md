# Stage-Based Interface

## Overview

The stage-based interface provides explicit CLI flags (`--extract`, `--adjust`, `--render`) for each pipeline operation, making workflows clear and composable.

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
python -m cvextract.cli --extract source=cv.docx --target output/ --verbosity debug

# Extract + Apply
python -m cvextract.cli \
  --extract source=cv.docx \
  --render template=template.docx \
  --target output/ \
  --verbosity debug

# Extract + Adjust + Apply
python -m cvextract.cli \
  --extract source=cv.docx \
  --adjust name=openai-company-research customer-url=https://example.com \
  --render template=template.docx \
  --target output/ \
  --verbosity debug

# Apply only (from existing JSON)
python -m cvextract.cli \
  --render template=template.docx data=cv.json \
  --target output/ \
  --verbosity debug
```

## Configuration

### Stage Flags

- **`--extract`**: Extract CV data from source file
  - Required params: `source=<path>`
  - Optional params: `name=<extractor>`, `output=<path>`, `verifier=<verifier-name>`, `skip-verify`

- **`--adjust`**: Adjust CV data (can be repeated for chaining)
  - Required params: `name=<adjuster>`, adjuster-specific params
  - Optional params: `data=<path>` (when not chained), `output=<path>`, `openai-model=<model>`, `verifier=<verifier-name>`, `skip-verify`, `dry-run`

- **`--render`**: Apply CV data to template
  - Required params: `template=<path>`
  - Optional params: `data=<path>` (when not chained), `output=<path>`, `verifier=<verifier-name>`, `skip-verify`

### Global Options

- **`--target <dir>`**: Output directory (required)
- **`--list {extractors,adjusters,renderers}`**: List available components
-- **`--verbosity {minimal,verbose,debug}`**: Output verbosity level (default: minimal)
  - `minimal`: One line per file with status icons, no third-party library output
  - `verbose`: Grouped per-file output blocks with warnings and major steps
  - `debug`: Full per-file output including application logs and stack traces
- **`--log-file <path>`**: Log file path
- **`--skip-all-verify`**: Skip verification across all stages (global override)

## Interfaces

### Auto-Chaining Behavior

When stages are chained:
- Extract → Adjust: Extracted JSON auto-passed to adjust
- Adjust → Render: Adjusted JSON auto-passed to render  
- Extract → Render: Extracted JSON auto-passed to render (skipping adjust)

The `data=` parameter is only needed when running stages standalone.

## Dependencies

### Internal Dependencies

- `cvextract.cli_gather` - Argument parsing
- `cvextract.cli_execute_pipeline` - Stage orchestration
- `cvextract.cli_execute_single` - Single-file stage execution
- `cvextract.cli_config.UserConfig` - Configuration storage

### Integration Points

- Implemented in `cvextract/cli.py` - Argument parser setup
- Validated in `cvextract/cli_gather.py` - Stage validation
- Executed in `cvextract/cli_execute_pipeline.py` - Stage orchestration

## Implementation History

The stage-based interface was designed to make the pipeline explicit and composable, replacing earlier monolithic commands.

**Key Files**:
- `cvextract/cli.py` - Argument definitions
- `cvextract/cli_gather.py` - Stage parsing
- `cvextract/cli_execute_single.py` - Single-file stage execution

## File Paths

- Implementation: `cvextract/cli.py`, `cvextract/cli_gather.py`, `cvextract/cli_execute_pipeline.py`, `cvextract/cli_execute_single.py`
- Tests: `tests/test_cli.py`
- Documentation: Main README.md "CLI Interface" section

## Related Documentation

- [CLI Architecture](../README.md)
- [Named Flags](../named-flags/README.md)
- [Batch Processing](../batch-processing/README.md)
- Main README: "CLI Interface" section
