# Directory Structure Preservation

## Overview

Directory structure preservation maintains the source directory hierarchy in all output paths, ensuring organized results that mirror input organization.

## Status

**Active** - Core CLI feature

## Description

When processing files from nested directories, cvextract:
1. **Calculates Relative Paths**: Determines each file's location relative to source root
2. **Preserves in Outputs**: Creates same directory structure in all output folders
3. **Applies Consistently**: Works across all stages and output types

## Entry Points

### CLI Usage

```bash
# Source structure:
# /source/teams/backend/engineer1.docx
# /source/teams/backend/engineer2.docx
# /source/teams/frontend/designer1.docx

python -m cvextract.cli \
  --extract source=/source/teams \
  --apply template=template.docx \
  --target output/

# Output structure:
# output/structured_data/backend/engineer1.json
# output/structured_data/backend/engineer2.json
# output/structured_data/frontend/designer1.json
# output/documents/backend/engineer1_NEW.docx
# output/documents/backend/engineer2_NEW.docx
# output/documents/frontend/designer1_NEW.docx
```

## Configuration

### Path Calculation

```python
# In cli_execute.py
if config.input_dir:
    source_base = config.input_dir.resolve()
else:
    source_base = source.parent.resolve() if source.is_file() else source.resolve()

rel_path = input_file.parent.resolve().relative_to(source_base)

# Output paths include relative structure
json_output = json_dir / rel_path / f"{input_file.stem}.json"
doc_output = documents_dir / rel_path / f"{input_file.stem}_NEW.docx"
```

### All Output Types

Structure preserved in:
- `structured_data/` - Extracted JSON
- `adjusted_structured_data/` - Adjusted JSON  
- `documents/` - Rendered DOCX
- `research_data/` - Company research caches
- `verification_structured_data/` - Roundtrip verification JSON

## Interfaces

### Single-File Mode

```python
# Source base determined from source path
source_base = source.parent.resolve()
```

### Parallel Mode

```python
# Source base explicitly set to scan root
config.input_dir = source_dir
```

## Dependencies

### Internal Dependencies

- `cvextract.cli_config.UserConfig.input_dir` - Source base path
- `cvextract.cli_execute` - Path calculation logic

### Integration Points

- Used in both single-file and parallel modes
- Applied to all output types (JSON, DOCX, research)

## Test Coverage

Tested in:
- `tests/test_cli.py` - Directory structure tests
- `tests/test_pipeline.py` - Multi-file structure verification

## Implementation History

Structure preservation was added to support organizational hierarchies (teams, departments) in batch processing.

**Key Files**:
- `cvextract/cli_execute.py` - Path calculation
- `cvextract/cli_parallel.py` - Parallel mode structure handling

## Use Cases

### Team Organization

```bash
# Input: /cvs/{team_name}/{person}.docx
# Output: /output/documents/{team_name}/{person}_NEW.docx
python -m cvextract.cli \
  --extract source=/cvs \
  --apply template=template.docx \
  --target /output
```

### Multi-Project

```bash
# Input: /projects/{project}/{role}/{cv}.docx
# Output: /output/structured_data/{project}/{role}/{cv}.json
python -m cvextract.cli \
  --extract source=/projects \
  --target /output
```

### Archive Preservation

```bash
# Maintain year/month structure
# Input: /archive/2025/01/{cv}.docx
# Output: /converted/2025/01/{cv}_NEW.docx
python -m cvextract.cli \
  --extract source=/archive \
  --apply template=new_template.docx \
  --target /converted
```

## File Paths

- Implementation: `cvextract/cli_execute.py` (path calculation logic)
- Tests: `tests/test_cli.py`
- Documentation: Main README.md "Complex Directory Structure Preservation" section

## Related Documentation

- [CLI Architecture](../README.md)
- [Batch Processing](../batch-processing/README.md)
- [Parallel Processing](../parallel-processing/README.md)
- Main README: "Complex Directory Structure Preservation" example
