# CLI Area

## Purpose

The CLI area provides a command-line interface with stage-based architecture, modern parameter syntax, and support for both single-file and batch processing modes.

## Features

- [Stage-Based Interface](stage-based-interface/README.md) - Explicit flags for extract/adjust/apply operations
- [Batch Processing](batch-processing/README.md) - Process multiple files recursively from directories
- [Parallel Processing](parallel-processing/README.md) - Multi-worker parallel file processing
- [Directory Structure Preservation](directory-structure-preservation/README.md) - Maintains source directory hierarchy
- [Named Flags](named-flags/README.md) - Modern key=value parameter syntax
- [Run Input Object](run-input-object/README.md) - Internal workflow input abstraction for future metadata enrichment

## Architectural Notes

### Design Principles

1. **Stage-Based**: Explicit `--extract`, `--adjust`, `--apply` flags for each operation
2. **Chainable**: Stages automatically pass data to next stage
3. **Explicit Paths**: All input/output paths determined upfront, passed explicitly to subsystems
4. **Modern Syntax**: `key=value` format for all parameters
5. **Composable**: Flags can be combined in any valid order

### Key Components

- **Main Entry**: `cvextract/cli.py` - Argument parsing and command dispatch
- **Config**: `cvextract/cli_config.py` - Configuration data structures
- **Gather**: `cvextract/cli_gather.py` - Parse and validate CLI arguments
- **Prepare**: `cvextract/cli_prepare.py` - Input file collection
- **Execute**: `cvextract/cli_execute.py` - Pipeline orchestration
- **Parallel**: `cvextract/cli_parallel.py` - Multi-worker batch processing

### Data Flow

```
CLI Args
  │
  v
[Parse & Validate]
  │
  v
UserConfig
  │
  ├──> Single File Mode
  │      │
  │      v
  │    [execute_pipeline]
  │
  └──> Parallel Mode
         │
         v
       [execute_parallel_pipeline]
```

### Integration Points

- **Extractors**: Via `--extract name=<extractor>`
- **Adjusters**: Via `--adjust name=<adjuster> <params>`
- **Renderers**: Via `--apply template=<path>`
- **Pipeline**: Orchestrates all operations via `cvextract.pipeline`

## Dependencies

- **Internal**: All cvextract modules (extractors, adjusters, renderers, verifiers, pipeline)
- **External**: `argparse` (CLI parsing), `multiprocessing` (parallel mode)

## File References

- Main: `cvextract/cli.py`
- Config: `cvextract/cli_config.py`
- Gather: `cvextract/cli_gather.py`
- Prepare: `cvextract/cli_prepare.py`
- Execute: `cvextract/cli_execute.py`
- Parallel: `cvextract/cli_parallel.py`
- Logging: `cvextract/logging_utils.py`
