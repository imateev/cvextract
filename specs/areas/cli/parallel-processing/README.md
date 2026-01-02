# Parallel Processing

## Overview

Parallel processing enables multi-worker concurrent file processing for high-throughput batch operations.

## Status

**Active** - Production feature

## Description

Features:
1. **Multi-Worker**: Uses Python `multiprocessing` to process files concurrently
2. **Worker Pools**: Configurable number of worker processes (`n=<count>`)
3. **Pre-Research**: Optional company research before parallel execution
4. **Independent Workers**: Each worker processes files independently
5. **Progress Tracking**: Real-time progress and error reporting

## Entry Points

### CLI Usage

```bash
# Parallel extraction (10 workers)
python -m cvextract.cli \
  --parallel source=/path/to/cv_folder n=10 \
  --extract \
  --target output/

# Parallel extract + adjust + apply (20 workers)
export OPENAI_API_KEY="sk-proj-..."
python -m cvextract.cli \
  --parallel source=/data/consultants n=20 \
  --extract \
  --adjust name=openai-company-research customer-url=https://target-company.com \
  --apply template=template.docx \
  --target output/
```

## Configuration

### Parameters

- **`source=<dir>`**: Directory containing input files (required)
- **`n=<count>`**: Number of worker processes (required, e.g., `n=10`)

### Worker Configuration

Each worker receives:
- Same stage configuration (extract, adjust, apply params)
- Individual input file path
- Shared output directories
- Independent logging

### Optimization: Pre-Research

When using company research adjuster, the main process performs research once before spawning workers:

```python
# In cli_parallel.py
if company_research_adjuster:
    # Pre-research in main process
    research = do_company_research(customer_url, cache_path)
    # All workers reuse cached research
```

## Interfaces

### Worker Function

```python
def _worker_process_file(args):
    """Worker function executed in separate process."""
    config, input_file = args
    
    # Each worker runs execute_pipeline independently
    return execute_pipeline(config_for_file)
```

### Process Pool

```python
# In execute_parallel_pipeline
with multiprocessing.Pool(processes=num_workers) as pool:
    results = pool.map(_worker_process_file, worker_args)
```

## Dependencies

### Internal Dependencies

- `cvextract.cli_execute.execute_pipeline()` - Per-file processing
- `cvextract.cli_prepare._collect_inputs()` - File discovery
- `cvextract.ml_adjustment` - Pre-research optimization

### External Dependencies

- `multiprocessing` - Process pool management

### Integration Points

- Triggered by `--parallel` flag
- Uses same pipeline as single-file mode
- Integrates with all stages (extract, adjust, apply)

## Test Coverage

Tested in:
- `tests/test_cli_parallel.py` - Parallel execution tests
- `tests/test_pipeline.py` - Multi-file integration tests

## Implementation History

Parallel processing was added to handle large-scale CV migrations (hundreds of consultants).

**Key Files**:
- `cvextract/cli_parallel.py` - Parallel execution implementation
- `cvextract/cli_execute.py` - Single-file execution (reused by workers)

## Open Questions

1. **Error Handling**: Should we support partial failure modes (some files succeed)?
2. **Resource Limits**: Should we auto-detect optimal worker count?
3. **Progress UI**: Should we add progress bar or percentage display?
4. **Retry**: Should workers retry failed files automatically?

## Performance Characteristics

- **Speedup**: Near-linear with worker count (up to CPU core limit)
- **Memory**: Each worker loads full pipeline (consider RAM limits)
- **I/O**: May be I/O-bound with many workers on slow storage
- **API Limits**: OpenAI rate limits may constrain throughput

## Best Practices

### Worker Count Selection

```bash
# Conservative: 4-8 workers
python -m cvextract.cli --parallel source=cvs/ n=8 --extract --target out/

# Aggressive: Match CPU cores
python -m cvextract.cli --parallel source=cvs/ n=16 --extract --target out/

# With OpenAI: Limit to avoid rate limits
python -m cvextract.cli --parallel source=cvs/ n=5 \
  --extract name=openai-extractor \
  --target out/
```

### Error Tracking

```bash
# Use log file to track worker errors
python -m cvextract.cli \
  --parallel source=cvs/ n=10 \
  --extract \
  --target out/ \
  --log-file out/parallel.log \
  --debug
```

## File Paths

- Implementation: `cvextract/cli_parallel.py`
- Worker Execution: `cvextract/cli_execute.py` (reused)
- Tests: `tests/test_cli_parallel.py`
- Documentation: Main README.md "Batch Processing - Extract Multiple Files" section

## Related Documentation

- [CLI Architecture](../README.md)
- [Batch Processing](../batch-processing/README.md)
- [Directory Structure Preservation](../directory-structure-preservation/README.md)
- Main README: Parallel processing examples
