# Batch Processing

## Overview

Batch processing enables recursive processing of multiple files from directories while preserving source directory structure in outputs.

## Status

**Active** - Core CLI feature

## Description

Features:
1. **Directory Input**: `source=<dir>` processes all matching files recursively
2. **Automatic Discovery**: Finds `.docx`, `.txt`, `.json` files based on stage
3. **Structure Preservation**: Maintains source directory hierarchy in outputs
4. **Same Config**: All files use same stage configuration

## Entry Points

### CLI Usage

```bash
# Extract all CVs from directory
python -m cvextract.cli \
  --extract source=/path/to/cv_folder \
  --target output/

# Extract + Render for entire folder
python -m cvextract.cli \
  --extract source=/path/to/cv_folder \
  --render template=template.docx \
  --target output/

# Directory structure preserved:
# /path/to/cv_folder/team1/engineer.docx
#   → output/structured_data/team1/engineer.json
#   → output/documents/team1/engineer_NEW.docx
```

## Configuration

### Directory Processing Rules

- **Extract**: Processes all `.docx` files (or `.txt` if using openai-extractor)
- **Adjust**: Processes all `.json` files when `data=<dir>` specified
- **Render**: Processes all `.json` files when `data=<dir>` specified

### Output Structure

```
target/
├── structured_data/
│   └── {preserved_structure}/
│       └── {filename}.json
├── adjusted_structured_data/
│   └── {preserved_structure}/
│       └── {filename}.json
├── documents/
│   └── {preserved_structure}/
│       └── {filename}_NEW.docx
└── research_data/
    └── {preserved_structure}/
        └── {filename}/
            └── {company_url}.json
```

## Interfaces

### File Discovery

```python
# In cli_prepare.py
def _collect_inputs(source, is_extraction, template_path):
    if source.is_dir():
        # Recursively find matching files
        pattern = "**/*.docx" if is_extraction else "**/*.json"
        return list(source.glob(pattern))
    else:
        return [source]
```

### Structure Preservation

```python
# In cli_execute_extract.py
source_base = config.input_dir.resolve()
rel_path = input_file.parent.resolve().relative_to(source_base)

# Output paths include relative structure
json_output = config.workspace.json_dir / rel_path / f"{input_file.stem}.json"
```

## Dependencies

### Internal Dependencies

- `cvextract.cli_prepare._collect_inputs()` - File discovery
- `cvextract.cli_execute_single` - Per-file processing with path preservation
- `cvextract.cli_execute_pipeline` - Single vs parallel orchestration

### Integration Points

- Used in both single-file and parallel modes
- Integrated with all stages (extract, adjust, render)

## Test Coverage

Tested in:
- `tests/test_cli.py` - Directory input handling
- `tests/test_pipeline.py` - Multi-file processing

## Implementation History

Batch processing was added to support real-world use cases where entire teams/departments of CVs need processing.

**Key Files**:
- `cvextract/cli_prepare.py` - File discovery
- `cvextract/cli_execute_single.py` - Per-file execution

## File Paths

- Implementation: `cvextract/cli_prepare.py`, `cvextract/cli_execute_single.py`, `cvextract/cli_execute_pipeline.py`
- Tests: `tests/test_cli.py`
- Documentation: Main README.md "Batch Processing" examples

## Related Documentation

- [CLI Architecture](../README.md)
- [Parallel Processing](../parallel-processing/README.md)
- [Directory Structure Preservation](../directory-structure-preservation/README.md)
- Main README: "Batch Processing" section
