# Run Input Object

## Status
Active

## Purpose

The Run Input Object is an internal data structure that encapsulates workflow input file paths and positions the pipeline for future metadata enrichment without changing the public CLI interface.

## Overview

The `RunInput` class is a lightweight dataclass that wraps file paths flowing through the pipeline. It serves as an internal abstraction layer between the CLI boundary and pipeline processing stages, enabling future per-run metadata capture without requiring changes to user-facing APIs or breaking existing workflows.

## Key Concepts

### Internal Representation

The `RunInput` object is constructed at the CLI boundary and flows through all internal pipeline stages (extract, adjust, apply). External users never interact with it directly - they continue to provide file paths via CLI arguments as they always have.

### Backward Compatibility

All pipeline functions that accept `RunInput` also accept plain `Path` objects for backward compatibility. This ensures existing code and tests continue to work without modification.

### Future Extensibility

The `RunInput` object is positioned to capture metadata such as:
- Timestamps (when file entered pipeline)
- Source context (original directory, batch identifier)
- Per-file options (custom extractor settings, rendering preferences)
- Processing lineage (which stages have processed this file)

No additional metadata is captured in the current implementation - this feature lays the groundwork for future enhancements.

## Implementation

### Module Location

`cvextract/run_input.py`

### Core Class

```python
@dataclass
class RunInput:
    """
    Internal representation of a workflow input file.
    
    Encapsulates the file path and positions for future metadata enrichment.
    
    Attributes:
        file_path: Path to the workflow input file
    """
    file_path: Path
    
    @classmethod
    def from_path(cls, path: Path) -> RunInput:
        """Construct a RunInput from a Path object."""
        return cls(file_path=path)
```

### Construction Point

`RunInput` objects are constructed in `cli_execute.py` at the CLI boundary:

```python
# Single file processing
input_file = inputs[0]

# Create RunInput object at CLI boundary
run_input = RunInput.from_path(input_file)

# Pass to pipeline
extract_ok, extract_errs, extract_warns = extract_single(
    run_input, out_json, config.debug, extractor=extractor
)
```

### Pipeline Integration

Pipeline functions accept `Union[Path, RunInput]` for backward compatibility:

```python
def extract_single(
    source: Union[Path, RunInput], 
    out_json: Path, 
    debug: bool,
    extractor: Optional[CVExtractor] = None
) -> tuple[bool, List[str], List[str]]:
    """Extract and verify a single file."""
    # Handle both Path and RunInput
    source_file = source.file_path if isinstance(source, RunInput) else source
    # ... rest of implementation
```

## Integration Points

### CLI Execute (`cli_execute.py`)
- Constructs `RunInput` from file paths at CLI boundary
- Passes `RunInput` to `extract_single` and other pipeline helpers

### Pipeline Helpers (`pipeline_helpers.py`)
- `extract_single`: Accepts `RunInput` or `Path`
- `render_and_verify`: Uses `RunInput` for roundtrip extraction

### Pipeline Highlevel (`pipeline_highlevel.py`)
- `extract_cv_structure`: Accepts `RunInput` or `Path`
- `process_single_docx`: Accepts `RunInput` or `Path`

### Parallel Processing (`cli_parallel.py`)
- Imports `RunInput` module (ready for future integration)

## Testing

Tests verify both `RunInput` construction and backward compatibility with `Path` objects:

- `test_run_input.py`: Core `RunInput` tests
  - Construction via `from_path` and direct initialization
  - Path type preservation
  - Integration with pipeline functions
  - Backward compatibility with `Path` objects

## User Impact

**No user-facing changes.** This is an internal refactoring that:
- Does not change CLI syntax or behavior
- Does not change input/output file formats
- Does not change pipeline processing logic
- Does not require user code changes

## Future Extensions

Once this foundation is in place, future enhancements can add metadata without changing the internal API:

- **Timestamps**: Capture when file entered pipeline
- **Source Context**: Track original directory, batch ID, etc.
- **Per-File Options**: Custom extractor/renderer settings per file
- **Processing Lineage**: Which stages processed this file
- **Performance Metrics**: Track processing time per stage

All future extensions will be additive and internal - the public CLI interface will remain unchanged.

## Dependencies

- **Internal**: None (pure internal abstraction)
- **External**: Python `dataclasses`, `pathlib`

## File References

- Core: `cvextract/run_input.py`
- CLI Execute: `cvextract/cli_execute.py`
- Pipeline Helpers: `cvextract/pipeline_helpers.py`
- Pipeline Highlevel: `cvextract/pipeline_highlevel.py`
- Tests: `tests/test_run_input.py`
