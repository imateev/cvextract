# Run Input Object

## Status
Active

## Purpose

The Run Input Object is an internal data structure that encapsulates the complete per-file workflow state, including all input and output paths and diagnostics (errors and warnings) for a single file processing run.

## Overview

The `RunInput` class is a dataclass that owns all file paths required and produced by the workflow, with each stage reading its required inputs from `RunInput` and recording its outputs back into it. It serves as the single source of truth for per-file workflow state, enabling clear data flow between workflow stages without passing raw path primitives.

Each `RunInput` instance is created **per input file** and is used exclusively for work related to that file. It is not shared across files or runs.

## Key Concepts

### Single Source of Truth

The `RunInput` object owns all file paths for a single file's workflow:
- **Input**: Original source file path
- **Extracted JSON**: Path to extracted CV data (set by extract stage)
- **Adjusted JSON**: Path to adjusted CV data (set by adjust stage if applicable)
- **Rendered Output**: Path to final rendered document (set by render stage if applicable)

### Per-File Workflow State

Each `RunInput` represents one file's journey through the pipeline:
- Created at the CLI boundary with the original file path
- Flows through extract → adjust → render stages
- Each stage updates it with newly produced paths
- Accumulates errors and warnings encountered during processing

### Internal Representation

The `RunInput` object is constructed at the CLI boundary and flows through all internal pipeline stages. External users never interact with it directly - they continue to provide file paths via CLI arguments as they always have.

### Backward Compatibility

All pipeline functions that accept `RunInput` also accept plain `Path` objects for backward compatibility. This ensures existing code and tests continue to work without modification.

## Implementation

### Module Location

`cvextract/run_input.py`

### Core Class

```python
@dataclass
class RunInput:
    """
    Internal representation of a complete per-file workflow state.
    
    Attributes:
        file_path: Path to the original workflow input file
        extracted_json_path: Path to extracted JSON output (set by extract stage)
        adjusted_json_path: Path to adjusted JSON output (set by adjust stage)
        rendered_output_path: Path to final rendered document (set by render stage)
        errors: List of error messages encountered during processing
        warnings: List of warning messages encountered during processing
    """
    file_path: Path
    extracted_json_path: Optional[Path] = None
    adjusted_json_path: Optional[Path] = None
    rendered_output_path: Optional[Path] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    @classmethod
    def from_path(cls, path: Path) -> RunInput:
        """Construct a RunInput from a Path object."""
        return cls(file_path=path)
    
    def add_error(self, error: str) -> None:
        """Add an error message to this run."""
        self.errors.append(error)
    
    def add_warning(self, warning: str) -> None:
        """Add a warning message to this run."""
        self.warnings.append(warning)
    
    def has_errors(self) -> bool:
        """Check if any errors have been recorded."""
        return len(self.errors) > 0
    
    def has_warnings(self) -> bool:
        """Check if any warnings have been recorded."""
        return len(self.warnings) > 0
```

### Construction Point

`RunInput` objects are constructed in `cli_execute.py` at the CLI boundary:

```python
# Single file processing
input_file = inputs[0]

# Create RunInput object at CLI boundary
run_input = RunInput.from_path(input_file)
```

### Workflow Stage Responsibilities

#### Extract Stage
- **Reads**: `run_input.file_path` (original source file)
- **Writes**: `run_input.extracted_json_path` (extracted JSON output)
- **Records**: Errors and warnings to `run_input.errors` and `run_input.warnings`

#### Adjust Stage
- **Reads**: `run_input.extracted_json_path` (extracted JSON)
- **Writes**: `run_input.adjusted_json_path` (adjusted JSON output)
- **Records**: Errors to `run_input.errors` if adjustment fails

#### Render Stage
- **Reads**: `run_input.adjusted_json_path` (if adjusted) or `run_input.extracted_json_path` (final JSON to render)
- **Writes**: `run_input.rendered_output_path` (final rendered document)
- **Records**: Errors and warnings to `run_input.errors` and `run_input.warnings`

### Pipeline Integration

#### CLI Execute (`cli_execute.py`)
- Constructs `RunInput` from file path at CLI boundary
- Passes `RunInput` to `extract_single` and other pipeline helpers
- Reads `adjusted_json_path` from `RunInput` after adjustment
- Passes `run_input` to `render_and_verify` for final rendering

#### Pipeline Helpers (`pipeline_helpers.py`)
- `extract_single`: Accepts `RunInput` or `Path`, records `extracted_json_path` and diagnostics
- `render_and_verify`: Accepts optional `run_input`, records `rendered_output_path` and diagnostics

#### Pipeline Highlevel (`pipeline_highlevel.py`)
- `extract_cv_structure`: Accepts `RunInput` or `Path`
- `process_single_docx`: Accepts `RunInput` or `Path`

#### Parallel Processing (`cli_parallel.py`)
- Imports `RunInput` module (ready for future integration)

## Testing

Tests verify both `RunInput` construction and backward compatibility with `Path` objects:

- `test_run_input.py`: Comprehensive `RunInput` tests
  - Construction via `from_path` and direct initialization
  - Path type preservation
  - Setting and retrieving all workflow paths
  - Adding and checking errors and warnings
  - Integration with pipeline functions
  - Verification that pipeline stages record outputs to `RunInput`
  - Verification that pipeline stages record diagnostics to `RunInput`
  - Backward compatibility with `Path` objects

## User Impact

**No user-facing changes.** This is an internal refactoring that:
- Does not change CLI syntax or behavior
- Does not change input/output file formats
- Does not change pipeline processing logic
- Does not require user code changes

## Future Extensions

The `RunInput` foundation enables future enhancements without changing the internal API:

- **Timestamps**: Capture when file entered pipeline and when each stage completed
- **Source Context**: Track original directory, batch ID, etc.
- **Per-File Options**: Custom extractor/renderer settings per file
- **Processing Lineage**: Which stages processed this file, in what order
- **Performance Metrics**: Track processing time per stage
- **Richer Diagnostics**: Structured error/warning objects with context

All future extensions will be additive and internal - the public CLI interface will remain unchanged.

## Dependencies

- **Internal**: None (pure internal abstraction)
- **External**: Python `dataclasses`, `pathlib`, `typing`

## File References

- Core: `cvextract/run_input.py`
- CLI Execute: `cvextract/cli_execute.py`
- Pipeline Helpers: `cvextract/pipeline_helpers.py`
- Pipeline Highlevel: `cvextract/pipeline_highlevel.py`
- Tests: `tests/test_run_input.py`
