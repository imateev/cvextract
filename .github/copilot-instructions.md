# Copilot Instructions for cvextract

## Project Overview

cvextract is a Python tool for extracting structured data from CV/resume documents and rendering them using templates. It separates CV content from presentation, enabling consistent formatting and easier maintenance.

**Core Concept**: Extract CV data from source documents (e.g., DOCX) → Store as structured JSON → Apply to templates → Generate formatted output documents.

## Architecture

The project follows a **pluggable architecture** with four main component types:

### 1. Extractors (`cvextract/extractors/`)
- **Purpose**: Extract structured CV data from various source formats
- **Base class**: `CVExtractor` (abstract base class in `base.py`)
- **Implementations**: `DocxCVExtractor`, `OpenAICVExtractor`
- **Registry**: `extractor_registry.py` manages available extractors
- **Contract**: All extractors return a dict conforming to `cvextract/contracts/cv_schema.json`

### 2. Renderers (`cvextract/renderers/`)
- **Purpose**: Render CV data to output formats using templates
- **Base class**: `CVRenderer` (abstract base class in `base.py`)
- **Implementations**: `DocxCVRenderer`
- **Registry**: `renderer_registry.py` manages available renderers
- **Contract**: Accept CV data dict and template path, return rendered output path

### 3. Adjusters (`cvextract/adjusters/`)
- **Purpose**: Modify CV data for specific purposes (e.g., tailoring to job/company)
- **Base class**: `CVAdjuster` (abstract base class in `base.py`)
- **Implementations**: `OpenAICompanyResearchAdjuster`, `OpenAIJobSpecificAdjuster`
- **Registry**: `adjuster_registry.py` manages available adjusters
- **Chaining**: Multiple adjusters can be chained together in sequence

### 4. Verifiers (`cvextract/verifiers/`)
- **Purpose**: Validate extracted/adjusted CV data for correctness and completeness
- **Base class**: `CVVerifier` (abstract base class in `base.py`)
- **Implementations**: `SchemaVerifier`, `DataVerifier`, `ComparisonVerifier`, `CompanyProfileVerifier`
- **Registry**: `verifier_registry.py` manages available verifiers

## Technology Stack

- **Python**: 3.10, 3.11, 3.12 (see `.github/workflows/ci.yml`)
- **Core Dependencies**:
  - `lxml`: XML parsing for DOCX files
  - `docxtpl`: DOCX template rendering
  - `requests`: HTTP requests for web scraping
  - `openai`: OpenAI API integration for AI-powered extraction/adjustment
- **Testing**: `pytest` with `pytest-cov` for coverage
- **Build**: `setuptools` via `pyproject.toml`

## Code Style and Conventions

### General Python Conventions
- Use `from __future__ import annotations` at the top of files for forward compatibility
- Import ordering: standard library → third-party → local imports
- Use type hints with `typing` module (`Dict`, `List`, `Optional`, `Any`)
- Use `pathlib.Path` for file paths, not strings
- Prefer explicit over implicit (clear variable names, explicit returns)

### Documentation
- **Docstrings**: Use triple-quoted strings with clear descriptions
- **Module docstrings**: Start each module with a docstring explaining its purpose
- **Class docstrings**: Describe the class purpose and its role in the architecture
- **Method docstrings**: Include Args, Returns, and Raises sections for public methods
- See examples in `cvextract/extractors/base.py` and `cvextract/renderers/base.py`

### Naming Conventions
- **Classes**: PascalCase (e.g., `CVExtractor`, `DocxCVRenderer`)
- **Functions/Methods**: snake_case (e.g., `extract_cv_structure`, `render_and_verify`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `LOG`, `PROJECT_ROOT`)
- **Private members**: Prefix with underscore (e.g., `_internal_helper`)

### Error Handling
- Raise specific exceptions with clear messages
- Use `FileNotFoundError` for missing files
- Use `ValueError` for invalid parameters or data
- Include context in error messages (e.g., file paths, expected vs actual values)
- See examples in extractor/renderer base classes

### Pluggable Components
When adding new extractors, renderers, adjusters, or verifiers:
1. Inherit from the appropriate base class
2. Implement all abstract methods
3. Register in the corresponding registry module
4. Add tests following existing test patterns
5. Update README if adding user-facing functionality

## Testing Practices

### Test Organization
- All tests in `tests/` directory
- Test file naming: `test_<module_name>.py`
- Test class naming: `Test<ComponentName>` (e.g., `TestDocxCVExtractor`)
- Test method naming: `test_<behavior_being_tested>` (descriptive names)

### Testing Framework
- Use `pytest` for all tests
- Use fixtures for reusable test data (see `tests/conftest.py`)
- Use `tmp_path` fixture for temporary files
- Use `monkeypatch` for mocking
- Prefer unit tests; use integration tests sparingly

### Test Patterns
- **Test abstractions**: Verify base classes cannot be instantiated
- **Test implementations**: Verify concrete classes work correctly
- **Test error cases**: Verify appropriate exceptions are raised
- **Test edge cases**: Empty inputs, missing fields, invalid data
- **Test integration**: Full pipeline workflows

See examples in `tests/test_extractors.py`, `tests/test_renderers.py`

### Coverage
- Aim for high coverage but prioritize meaningful tests
- Coverage reports generated automatically in CI
- Run locally: `python -m pytest tests/ --cov=cvextract --cov-report=term`

### Documentation
- All authoritative project documentation lives in the `specs/` directory.
- `specs/FEATURES.md` is the single source of truth for all implemented, planned, and proposed features.
- Any non-trivial change (feature, behavior, workflow, or refactor) should result in a documentation update.
- The `specs/areas/` directory is organized by domain and functional area.
- Each domain contains a `README.md` describing its purpose, concepts, and workflows.
- New features must update `specs/FEATURES.md` and the relevant `specs/areas/<domain>/` documentation.
- Complex areas may contain nested sub-directories, each with its own `README.md` describing a specific sub-system or pipeline.
- Avoid duplicating documentation across areas; instead, reference related domains where necessary.
- Documentation changes are expected to happen alongside code changes, not after the fact.

## Build and Development Commands

### Setup
```bash
# Install package in editable mode with dependencies
python -m pip install -e .

# Install with test dependencies
python -m pip install -e . pytest pytest-cov
```

### Running Tests
```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ -v --cov=cvextract --cov-report=xml --cov-report=term

# Run specific test file
python -m pytest tests/test_extractors.py -v

# Run specific test
python -m pytest tests/test_extractors.py::TestDocxCVExtractor::test_extract_returns_dict_with_required_keys -v
```

### Running the CLI
```bash
# Extract CV from DOCX
python -m cvextract.cli --extract source=/path/to/cv.docx --target /output

# Extract and apply template
python -m cvextract.cli --extract source=/path/to/cv.docx --apply template=/path/to/template.docx --target /output

# Batch processing with parallel workers
python -m cvextract.cli --parallel source=/path/to/cvs n=10 --extract --target /output

# List available extractors/renderers/adjusters
python -m cvextract.cli --list extractors
python -m cvextract.cli --list renderers
python -m cvextract.cli --list adjusters
```

## CV Data Schema

The CV data structure (defined in `cvextract/contracts/cv_schema.json`) has four main sections:

```json
{
  "identity": {
    "title": "Professional title",
    "full_name": "Full Name",
    "first_name": "First",
    "last_name": "Last"
  },
  "sidebar": {
    "languages": ["Python", "JavaScript"],
    "tools": ["Git", "Docker"],
    "certifications": ["AWS Certified"],
    "industries": ["Finance", "Healthcare"],
    "spoken_languages": ["English", "Spanish"],
    "academic_background": ["BS Computer Science"]
  },
  "overview": "Professional summary text",
  "experiences": [
    {
      "heading": "Jan 2020 – Present | Senior Engineer | Company",
      "description": "Description text",
      "bullets": ["Achievement 1", "Achievement 2"],
      "environment": ["Python", "AWS"]
    }
  ]
}
```

**Important**: All extractors, adjusters, and renderers must maintain this schema structure.

## Key Modules

- **`cli.py`**: Main CLI entry point (three-phase architecture: gather → prepare → execute)
- **`pipeline.py`**: Re-exports pipeline helpers for backward compatibility
- **`pipeline_helpers.py`**: Core pipeline utilities (extraction, rendering, verification)
- **`pipeline_highlevel.py`**: High-level API (`extract_cv_structure()`)
- **`logging_utils.py`**: Logging configuration and utilities
- **`output_controller.py`**: Controls output verbosity and buffering for parallel processing
- **`shared.py`**: Shared utilities and helper functions

## Development Workflow

1. **Start with tests**: Write tests first for new functionality
2. **Follow existing patterns**: Match the style of existing code
3. **Keep changes focused**: Small, incremental changes are preferred
4. **Run tests locally**: Verify tests pass before committing
5. **Update documentation**: Update README.md if adding user-facing features
6. **Check CI**: Ensure GitHub Actions workflows pass

## Contribution Guidelines

See `.github/CONTRIBUTING.md` for contribution policies. Key points:
- Bug fixes and small improvements are welcome
- Open an issue for non-trivial changes before submitting a PR
- Follow existing code style and architecture patterns
- Include tests for new functionality
- Keep changes focused and reasonably small

## Important Notes

- The project is experimental and intentionally opinionated
- Avoid large refactors without prior discussion
- Support for arbitrary CV layouts is out of scope
- Focus on the pluggable architecture patterns
- Maintain backward compatibility when possible
- XML safety is critical when rendering DOCX (see `cvextract/renderers/docx_renderer.py`)
