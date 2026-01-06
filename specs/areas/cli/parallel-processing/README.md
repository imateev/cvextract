# Parallel Processing

## Overview

Parallel processing enables multi-worker concurrent file processing for high-throughput batch operations.

## Status

**Active** - Production feature

## Description

Features:
1. **Multi-Worker**: Uses Python `ThreadPoolExecutor` to process files concurrently
2. **Worker Pools**: Configurable number of worker threads (`n=<count>`)
3. **File Type Selection**: Configurable file pattern matching (`file-type=<pattern>`)
4. **Progress Indicator**: Real-time progress display with completion percentage (e.g., `[5/20 | 25%]`)
5. **Pre-Research**: Optional company research before parallel execution
6. **Independent Workers**: Each worker processes files independently
7. **Clean Logging**: One concise line per completed file in parallel mode
8. **External Provider Log Control**: Optional capture of third-party library logs via `--debug-external`

## Entry Points

### CLI Usage

```bash
# Parallel extraction (10 workers, default .docx files)
python -m cvextract.cli \
  --parallel source=/path/to/cv_folder n=10 \
  --extract \
  --target output/

# Parallel extraction of text files using OpenAI extractor
export OPENAI_API_KEY="sk-proj-..."
python -m cvextract.cli \
  --parallel source=/path/to/text_cvs n=10 file-type=*.txt \
  --extract name=openai-extractor \
  --target output/

# Parallel extract + adjust + render (20 workers)
export OPENAI_API_KEY="sk-proj-..."
python -m cvextract.cli \
  --parallel source=/data/consultants n=20 \
  --extract \
  --adjust name=openai-company-research customer-url=https://target-company.com \
  --render template=template.docx \
  --target output/

# Parallel with external provider logging for debugging API interactions
export OPENAI_API_KEY="sk-proj-..."
python -m cvextract.cli \
  --parallel source=/path/to/cvs n=10 \
  --extract name=openai-extractor \
  --target output/ \
  --verbosity verbose \
  --verbosity debug \
  --debug-external
```

## Configuration

### Parameters

- **`source=<dir>`**: Directory containing input files (required)
- **`n=<count>`**: Number of worker threads (required, e.g., `n=10`)
- **`file-type=<pattern>`**: File pattern to match (optional, defaults to `*.docx`, e.g., `file-type=*.txt`)

### Global Flags

- **`--verbosity {minimal,verbose,debug}`**: Output verbosity level (default: minimal)
- **`--debug-external`**: Capture external provider logs (OpenAI, httpx, etc.) in parallel mode
  - By default, external provider logs are suppressed to ensure deterministic output
  - When enabled, logs are routed through buffered output controller and grouped per file
  - Only affects parallel mode; has no effect in single-file mode
- **`--debug`**: Enable application debug logging with stack traces
- **`--log-file <path>`**: Write all output to persistent log file

### Worker Configuration

Each worker receives:
- Same stage configuration (extract, adjust, render params)
- Individual input file path
- Shared output directories
- Independent logging

### Optimization: Pre-Research

When using company research adjuster, the main process performs research once before spawning workers:

```python
# In cli_parallel.py
if company_research_adjuster:
    # Pre-research in main process
    research = do_company_research(customer_url)
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
from concurrent.futures import ThreadPoolExecutor, as_completed

with ThreadPoolExecutor(max_workers=n_workers) as executor:
    # Submit all tasks
    future_to_file = {
        executor.submit(process_single_file_wrapper, file_path, config): file_path
        for file_path in files
    }
    
    # Process results as they complete with progress tracking
    for completed_count, future in enumerate(as_completed(future_to_file), 1):
        file_path = future_to_file[future]
        progress_pct = int((completed_count / total_files) * 100)
        progress_str = f"[{completed_count}/{total_files} | {progress_pct}%]"
        # Log with progress indicator
        LOG.info("%s %s %s", status_icon, progress_str, file_path.name)
```

## Dependencies

### Internal Dependencies

- `cvextract.cli_execute.execute_pipeline()` - Per-file processing
- `cvextract.cli_prepare._collect_inputs()` - File discovery
- `cvextract.adjusters` - Adjuster implementations for CV optimization

### External Dependencies

- `concurrent.futures.ThreadPoolExecutor` - Thread pool management

### Integration Points

- Triggered by `--parallel` flag
- Uses same pipeline as single-file mode
- Integrates with all stages (extract, adjust, render)

## Logging Behavior

### Default Behavior (No --debug-external)

In parallel mode, external provider logs (e.g., OpenAI SDK, httpx, httpcore, urllib3, requests) are **suppressed by default** to ensure:
- **Deterministic output**: No interleaved or duplicate logs
- **Clean console**: One line per file with status icons
- **Predictable behavior**: Same output format regardless of third-party library verbosity

This suppression is intentional and by design. Application logs (from cvextract) are still captured and displayed according to verbosity settings.

### With --debug-external Flag

When `--debug-external` is enabled:
1. External provider loggers are configured to route through the buffered output controller
2. Logs are captured per-file and grouped with application logs
3. Output remains deterministic and atomic (no interleaving)
4. External logs appear in the per-file output block based on verbosity level:
   - `minimal`: External logs suppressed
   - `verbose`: External INFO and above
   - `debug`: All external logs including DEBUG

**Use Cases for --debug-external**:
- Troubleshooting API authentication issues
- Debugging HTTP request/response patterns
- Investigating rate limiting or timeout errors
- Understanding OpenAI SDK behavior

**Not Recommended For**:
- Production batch processing (excessive noise)
- Normal operation (default suppression is optimal)

### Log Routing Architecture

```python
# Default (debug_external=False)
openai.logger -> CRITICAL+1 (suppressed)
httpx.logger -> CRITICAL+1 (suppressed)

# With --debug-external (debug_external=True)
openai.logger -> BufferingLogHandler -> per-file buffer -> atomic flush
httpx.logger -> BufferingLogHandler -> per-file buffer -> atomic flush
cvextract.logger -> BufferingLogHandler -> per-file buffer -> atomic flush
```

## Test Coverage

Tested in:
- `tests/test_cli_parallel.py` - Parallel execution tests
- `tests/test_pipeline.py` - Multi-file integration tests
- `tests/test_debug_external.py` - External provider log capture tests

## Implementation History

Parallel processing was added to handle large-scale CV migrations (hundreds of consultants).

**Key Files**:
- `cvextract/cli_parallel.py` - Parallel execution implementation
- `cvextract/cli_execute.py` - Single-file execution (reused by workers)
- `cvextract/output_controller.py` - Buffered output and external log control

**Recent Updates**:
- **v0.6.1+**: Added `--debug-external` flag for opt-in external provider log capture

## Open Questions

1. **Error Handling**: ✅ Implemented - Partial failure modes supported (some files can fail)
2. **Resource Limits**: Should we auto-detect optimal worker count?
3. **Progress UI**: ✅ Implemented - Progress indicator shows completion percentage
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
